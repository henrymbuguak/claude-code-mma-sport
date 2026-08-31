from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from events.models import Fighter, Ranking
from events.services.cito_client import CitoAPIError, CitoClient


def _first(data, *keys, default=None):
    for key in keys:
        if key in data and data[key] not in (None, ""):
            return data[key]
    return default


class Command(BaseCommand):
    help = "Sync UFC divisional rankings from the Cito API."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        client = CitoClient()
        max_calls = settings.CITO_RANKINGS_SYNC_MAX_API_CALLS_PER_RUN

        created = updated = 0
        fighters_created = 0
        had_failure = False

        # This endpoint does not honor `page` (confirmed: page=1 and page=2
        # return identical data) — only `limit` controls how much comes back
        # in one call. A single generous-limit call gets every division, so
        # there's no pagination loop here, unlike sync_upcoming_events. The
        # call-budget setting/check is kept anyway as a defensive guard in
        # case that behavior ever changes upstream.
        if client.calls_made < max_calls:
            try:
                payload = client.get_rankings(limit=250)
            except CitoAPIError as exc:
                self.stdout.write(self.style.ERROR(f"Failed to fetch rankings: {exc}"))
                had_failure = True
                payload = None
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"CITO_RANKINGS_SYNC_MAX_API_CALLS_PER_RUN ({max_calls}) already reached; "
                    "skipping."
                )
            )
            payload = None

        if payload is not None:
            batch = payload if isinstance(payload, list) else payload.get("data", [])
            for row in batch:
                fighter, fc = self._upsert_fighter(row, dry_run=dry_run)
                fighters_created += fc
                _, was_created = self._upsert_ranking(fighter, row, dry_run=dry_run)
                created += was_created
                updated += not was_created

        self.stdout.write(
            self.style.SUCCESS(
                f"Rankings: {created} created, {updated} updated. "
                f"Fighters created as placeholders: {fighters_created}. "
                f"API calls used: {client.calls_made}."
                + (" (dry run, no writes)" if dry_run else "")
            )
        )
        if had_failure:
            raise CommandError(
                "One or more Cito API calls failed during rankings sync; already-synced "
                "rankings from this run were kept, but the run did not complete cleanly."
            )

    def _upsert_fighter(self, row, dry_run):
        slug = _first(row, "fighterSlug", default=slugify(_first(row, "fighterName", default="")))
        nested = row.get("fighter") or {}
        record = nested.get("record") or {}
        defaults = {
            "slug": slug,
            "name": _first(row, "fighterName", default=slug),
            "nickname": nested.get("nickname") or "",
            "record": record.get("text") or nested.get("recordText") or "",
            "country": _first(row, "country") or nested.get("country") or "",
            "photo_url": nested.get("headshotUrl") or "",
        }
        if dry_run:
            existing = Fighter.objects.filter(cito_id=slug).first()
            return existing or Fighter(cito_id=slug, **defaults), existing is None
        fighter, created = Fighter.objects.get_or_create(cito_id=slug, defaults=defaults)
        return fighter, created

    @transaction.atomic
    def _upsert_ranking(self, fighter, row, dry_run):
        division = _first(row, "division", default="")
        defaults = {
            "rank": row.get("rank"),
            "rank_text": _first(row, "rankText", default=""),
            "is_champion": bool(row.get("isChampion", False)),
            "raw_data": row,
        }
        if dry_run:
            existing = Ranking.objects.filter(fighter=fighter, division=division).first()
            return existing, existing is None
        return Ranking.objects.update_or_create(
            fighter=fighter, division=division, defaults=defaults
        )

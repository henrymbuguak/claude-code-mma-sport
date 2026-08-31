import re
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.text import slugify

from events.models import Bout, Event, Fighter
from events.services.cito_client import CitoAPIError, CitoClient


def _first(data, *keys, default=None):
    for key in keys:
        if key in data and data[key] not in (None, ""):
            return data[key]
    return default


def _parse_start_time(data):
    raw = _first(data, "startTime", "start_time", "date", "startsAt")
    parsed = parse_datetime(raw) if isinstance(raw, str) else raw
    if parsed is None:
        raise ValueError(f"Could not parse event start time from {raw!r}")
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.utc)
    return parsed


def _event_id(data):
    return str(_first(data, "id", "eventId", "cito_id"))


def _event_slug(data, event_id):
    return _first(data, "slug", default=slugify(_first(data, "name", "title", default=event_id)))


def _venue(data):
    venue = _first(data, "venue", default={}) or {}
    if isinstance(venue, dict):
        return (
            _first(venue, "name", default=""),
            _first(venue, "city", default=""),
            _first(venue, "country", default=""),
        )
    # Some API responses give venue as a plain name string with city/country
    # as separate top-level fields rather than a nested object.
    return (
        venue,
        _first(data, "city", "venueCity", "venue_city", default=""),
        _first(data, "country", "venueCountry", "venue_country", default=""),
    )


CARD_SEGMENT_KEYWORDS = [
    ("early", Bout.CardSegment.EARLY_PRELIMS),
    ("prelim", Bout.CardSegment.PRELIMS),
    ("main", Bout.CardSegment.MAIN_CARD),
]


def _card_segment(data):
    raw = _first(data, "cardSegment", "card_segment", "cardSection", default="")
    normalized = raw.strip().lower()
    for keyword, segment in CARD_SEGMENT_KEYWORDS:
        if keyword in normalized:
            return segment
    return Bout.CardSegment.UNKNOWN


def _position_in_section(data):
    # "cardSectionOrder" is a section-group index (always 1 for every
    # bout in "Main Card"), not a per-bout position — the real position
    # is only available embedded in "cardPosition" (e.g. "Main Card 1",
    # "Main Card 2", ...).
    card_position = _first(data, "cardPosition", default="")
    match = re.search(r"(\d+)\s*$", card_position)
    return int(match.group(1)) if match else None


def _extract_fighters(bout_data):
    fighters_list = bout_data.get("fighters")
    if isinstance(fighters_list, list) and len(fighters_list) >= 2:
        ordered = sorted(fighters_list, key=lambda f: 0 if f.get("corner") == "red" else 1)
        return ordered[0], ordered[1]
    return (
        _first(bout_data, "fighterOne", "fighter_one", "fighter1", default={}),
        _first(bout_data, "fighterTwo", "fighter_two", "fighter2", default={}),
    )


def _fighter_id(data):
    return str(_first(data, "slug", "fighterSlug", "id", "fighterId", "cito_id"))


class Command(BaseCommand):
    help = "Sync upcoming UFC events and near-term fight cards from the Cito API."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        client = CitoClient()
        refresh_window = timedelta(days=settings.CITO_SYNC_BOUTS_REFRESH_WINDOW_DAYS)
        max_calls = settings.CITO_SYNC_MAX_API_CALLS_PER_RUN
        now = timezone.now()

        events_created = events_updated = 0
        bouts_created = bouts_updated = 0
        fighters_created = fighters_updated = 0
        budget_exceeded_warned = False
        had_failure = False

        page = 1
        while True:
            try:
                payload = client.get_upcoming_events(page=page)
            except CitoAPIError as exc:
                self.stdout.write(
                    self.style.ERROR(f"Failed to fetch page {page} of upcoming events: {exc}")
                )
                had_failure = True
                break

            batch = (
                payload
                if isinstance(payload, list)
                else payload.get("data", payload.get("results", []))
            )
            if not batch:
                break

            for event_data in batch:
                event, created = self._upsert_event(event_data, dry_run=dry_run)
                events_created += created
                events_updated += not created

                needs_bouts = event.bouts_synced_at is None or (
                    event.start_time - now <= refresh_window
                )
                if not needs_bouts:
                    continue

                if client.calls_made >= max_calls:
                    if not budget_exceeded_warned:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Reached CITO_SYNC_MAX_API_CALLS_PER_RUN ({max_calls}); "
                                "skipping remaining bout fetches."
                            )
                        )
                        budget_exceeded_warned = True
                    continue

                try:
                    bouts_payload = client.get_event_bouts(event.cito_id)
                except CitoAPIError as exc:
                    self.stdout.write(
                        self.style.ERROR(f"Failed to fetch bouts for event {event.cito_id}: {exc}")
                    )
                    had_failure = True
                    continue

                bc, bu, fc, fu = self._sync_bouts(event, bouts_payload, dry_run=dry_run)
                bouts_created += bc
                bouts_updated += bu
                fighters_created += fc
                fighters_updated += fu

                if not dry_run:
                    event.bouts_synced_at = now
                    event.save(update_fields=["bouts_synced_at"])

            page += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Events: {events_created} created, {events_updated} updated. "
                f"Bouts: {bouts_created} created, {bouts_updated} updated. "
                f"Fighters: {fighters_created} created, {fighters_updated} updated. "
                f"API calls used: {client.calls_made}."
                + (" (dry run, no writes)" if dry_run else "")
            )
        )

        if had_failure:
            raise CommandError(
                "One or more Cito API calls failed during sync; already-synced data from "
                "this run was kept, but the run did not complete cleanly — see errors above."
            )

    @transaction.atomic
    def _upsert_event(self, data, dry_run):
        event_id = _event_id(data)
        venue_name, venue_city, venue_country = _venue(data)
        defaults = {
            "slug": _event_slug(data, event_id),
            "name": _first(data, "name", "title", default=event_id),
            "start_time": _parse_start_time(data),
            "venue_name": venue_name,
            "venue_city": venue_city,
            "venue_country": venue_country,
            "status": Event.Status.UPCOMING,
            "poster_image_url": _first(
                data, "posterImageUrl", "poster_image_url", "imageUrl", default=""
            ),
            "raw_data": data,
        }
        if dry_run:
            existing = Event.objects.filter(cito_id=event_id).first()
            return existing or Event(cito_id=event_id, **defaults), existing is None
        event, created = Event.objects.update_or_create(cito_id=event_id, defaults=defaults)
        return event, created

    @transaction.atomic
    def _sync_bouts(self, event, bouts_payload, dry_run):
        bouts_created = bouts_updated = 0
        fighters_created = fighters_updated = 0
        bouts = (
            bouts_payload
            if isinstance(bouts_payload, list)
            else bouts_payload.get("data", bouts_payload.get("bouts", []))
        )

        for order, bout_data in enumerate(bouts, start=1):
            fighter_one_data, fighter_two_data = _extract_fighters(bout_data)
            fighter_one, fc1 = self._upsert_fighter(fighter_one_data, dry_run=dry_run)
            fighter_two, fc2 = self._upsert_fighter(fighter_two_data, dry_run=dry_run)
            fighters_created += fc1 + fc2
            fighters_updated += (not fc1) + (not fc2)

            bout_id = str(
                _first(bout_data, "id", "boutId", "cito_id", default=f"{event.cito_id}-{order}")
            )
            segment = _card_segment(bout_data)
            is_main_event = bool(
                _first(bout_data, "isMainEvent", "is_main_event", default=False)
            ) or (segment == Bout.CardSegment.MAIN_CARD and _position_in_section(bout_data) == 1)
            defaults = {
                "event": event,
                "fighter_one": fighter_one,
                "fighter_two": fighter_two,
                "weight_class": _first(bout_data, "weightClass", "weight_class", default=""),
                "card_segment": segment,
                "bout_order": _first(bout_data, "boutOrder", "order", default=order),
                "is_title_fight": bool(
                    _first(bout_data, "isTitleFight", "is_title_fight", "titleBout", default=False)
                ),
                "is_main_event": is_main_event,
                "raw_data": bout_data,
            }
            if dry_run:
                existing = Bout.objects.filter(cito_id=bout_id).first()
                bouts_created += existing is None
                bouts_updated += existing is not None
                continue
            _, created = Bout.objects.update_or_create(cito_id=bout_id, defaults=defaults)
            bouts_created += created
            bouts_updated += not created

        return bouts_created, bouts_updated, fighters_created, fighters_updated

    def _upsert_fighter(self, data, dry_run):
        # Some endpoints nest richer fighter data under "profile"; merge it
        # over the top-level entry so profile fields (slug, nickname, record)
        # take precedence while top-level-only fields (e.g. corner-specific
        # imageUrl) remain available as fallbacks.
        merged = {**data, **(data.get("profile") or {})}
        fighter_id = _fighter_id(merged)
        name = _first(merged, "name", "fighterName", default=fighter_id)
        record = _first(merged, "recordText", "record", default="")
        if isinstance(record, dict):
            record = record.get("text") or ""
        defaults = {
            "slug": _first(merged, "slug", "fighterSlug", default=slugify(name)),
            "name": name,
            "nickname": _first(merged, "nickname", default=""),
            "record": record,
            "country": _first(merged, "country", default=""),
            "photo_url": _first(
                merged, "photoUrl", "photo_url", "headshotUrl", "imageUrl", default=""
            ),
        }
        if dry_run:
            existing = Fighter.objects.filter(cito_id=fighter_id).first()
            return existing or Fighter(cito_id=fighter_id, **defaults), existing is None
        fighter, created = Fighter.objects.update_or_create(cito_id=fighter_id, defaults=defaults)
        return fighter, created

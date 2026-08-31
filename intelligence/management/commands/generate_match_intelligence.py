from datetime import timedelta

import anthropic
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from events.models import Bout, Event
from intelligence.models import MatchAnalysis
from intelligence.services.claude_analyst import generate_analysis


class Command(BaseCommand):
    help = "Generate AI match-intelligence analyses for near-term upcoming bouts."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--force", action="store_true")

    def handle(self, *args, **options):
        dry_run, force = options["dry_run"], options["force"]
        now = timezone.now()
        window_end = now + timedelta(days=settings.INTELLIGENCE_WINDOW_DAYS)

        bouts = (
            Bout.objects.select_related("event", "fighter_one", "fighter_two", "match_analysis")
            .filter(
                event__status=Event.Status.UPCOMING,
                event__start_time__gte=now,
                event__start_time__lte=window_end,
            )
            .order_by("event__start_time", "bout_order")
        )
        if not force:
            bouts = bouts.filter(match_analysis__isnull=True)
        bouts = list(bouts[: settings.INTELLIGENCE_MAX_ANALYSES_PER_RUN])

        generated = failures = 0
        for bout in bouts:
            self.stdout.write(f"Generating analysis for {bout}...")
            if dry_run:
                generated += 1
                continue
            try:
                text = generate_analysis(bout)
            except (
                anthropic.RateLimitError,
                anthropic.APIStatusError,
                anthropic.APIConnectionError,
            ) as exc:
                self.stdout.write(self.style.ERROR(f"Failed on {bout}: {exc}"))
                failures += 1
                continue

            MatchAnalysis.objects.update_or_create(
                bout=bout,
                defaults={"analysis_text": text, "model_used": settings.INTELLIGENCE_MODEL},
            )
            generated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Generated {generated} analyses"
                f"{' (dry run)' if dry_run else ''}, {failures} failed."
            )
        )
        if failures:
            raise CommandError(f"{failures} bout(s) failed; already-generated analyses were kept.")

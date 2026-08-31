from datetime import timedelta

import anthropic
import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from events.models import Event
from intelligence.models import MatchAnalysis

pytestmark = pytest.mark.django_db


def test_generates_analysis_for_upcoming_bout_in_window(mocker, make_event, make_bout):
    event = make_event(start_time=timezone.now() + timedelta(days=3))
    bout = make_bout(event)
    mocker.patch(
        "intelligence.management.commands.generate_match_intelligence.generate_analysis",
        return_value="A neutral analysis.",
    )

    call_command("generate_match_intelligence")

    analysis = MatchAnalysis.objects.get(bout=bout)
    assert analysis.analysis_text == "A neutral analysis."
    assert analysis.model_used == "claude-opus-5"


def test_skips_bout_outside_window(mocker, settings, make_event, make_bout):
    settings.INTELLIGENCE_WINDOW_DAYS = 7
    event = make_event(start_time=timezone.now() + timedelta(days=30))
    make_bout(event)
    generate_mock = mocker.patch(
        "intelligence.management.commands.generate_match_intelligence.generate_analysis",
        return_value="unused",
    )

    call_command("generate_match_intelligence")

    generate_mock.assert_not_called()
    assert MatchAnalysis.objects.count() == 0


def test_skips_non_upcoming_event(mocker, make_event, make_bout):
    event = make_event(status=Event.Status.COMPLETED, start_time=timezone.now() - timedelta(days=1))
    make_bout(event)
    generate_mock = mocker.patch(
        "intelligence.management.commands.generate_match_intelligence.generate_analysis",
        return_value="unused",
    )

    call_command("generate_match_intelligence")

    generate_mock.assert_not_called()


def test_skips_bout_with_existing_analysis_unless_forced(
    mocker, make_event, make_bout, make_match_analysis
):
    event = make_event(start_time=timezone.now() + timedelta(days=3))
    bout = make_bout(event)
    make_match_analysis(bout, analysis_text="Old analysis.")
    generate_mock = mocker.patch(
        "intelligence.management.commands.generate_match_intelligence.generate_analysis",
        return_value="New analysis.",
    )

    call_command("generate_match_intelligence")
    generate_mock.assert_not_called()
    assert MatchAnalysis.objects.get(bout=bout).analysis_text == "Old analysis."

    call_command("generate_match_intelligence", "--force")
    generate_mock.assert_called_once()
    assert MatchAnalysis.objects.get(bout=bout).analysis_text == "New analysis."


def test_respects_max_analyses_per_run(mocker, settings, make_event, make_bout):
    settings.INTELLIGENCE_MAX_ANALYSES_PER_RUN = 1
    event = make_event(start_time=timezone.now() + timedelta(days=3))
    make_bout(event, cito_id="b-1", bout_order=1)
    make_bout(event, cito_id="b-2", bout_order=2)
    mocker.patch(
        "intelligence.management.commands.generate_match_intelligence.generate_analysis",
        return_value="An analysis.",
    )

    call_command("generate_match_intelligence")

    assert MatchAnalysis.objects.count() == 1


def test_dry_run_creates_no_analyses(mocker, make_event, make_bout):
    event = make_event(start_time=timezone.now() + timedelta(days=3))
    make_bout(event)
    generate_mock = mocker.patch(
        "intelligence.management.commands.generate_match_intelligence.generate_analysis",
        return_value="unused",
    )

    call_command("generate_match_intelligence", "--dry-run")

    generate_mock.assert_not_called()
    assert MatchAnalysis.objects.count() == 0


def test_failure_on_one_bout_preserves_others_and_raises(mocker, make_event, make_bout):
    event = make_event(start_time=timezone.now() + timedelta(days=3))
    ok_bout = make_bout(event, cito_id="b-ok", bout_order=1)
    fail_bout = make_bout(event, cito_id="b-fail", bout_order=2)

    def side_effect(bout):
        if bout.pk == fail_bout.pk:
            raise anthropic.APIConnectionError(request=mocker.Mock())
        return "Generated fine."

    mocker.patch(
        "intelligence.management.commands.generate_match_intelligence.generate_analysis",
        side_effect=side_effect,
    )

    with pytest.raises(CommandError):
        call_command("generate_match_intelligence")

    assert MatchAnalysis.objects.filter(bout=ok_bout).exists()
    assert not MatchAnalysis.objects.filter(bout=fail_bout).exists()

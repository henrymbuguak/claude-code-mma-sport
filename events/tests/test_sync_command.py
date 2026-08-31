from datetime import timedelta

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from events.models import Bout, Event, Fighter

pytestmark = pytest.mark.django_db

API_BASE = "https://api.test.local"


@pytest.fixture(autouse=True)
def cito_settings(settings):
    settings.CITO_API_BASE_URL = API_BASE
    settings.CITO_API_KEY = "test-key"


def make_event_payload(event_id="evt-1", days_out=30):
    start = (timezone.now() + timedelta(days=days_out)).isoformat()
    return {
        "id": event_id,
        "slug": event_id,
        "name": "UFC 999: Test Card",
        "startTime": start,
        "venue": {"name": "Test Arena", "city": "Las Vegas", "country": "USA"},
    }


def make_bout_payload(bout_id="bout-1"):
    return {
        "id": bout_id,
        "fighterOne": {"id": f"{bout_id}-f1", "name": "Fighter One"},
        "fighterTwo": {"id": f"{bout_id}-f2", "name": "Fighter Two"},
        "weightClass": "Lightweight",
        "cardSegment": "main_card",
        "order": 1,
        "isTitleFight": False,
    }


def paginated_events_callback(pages):
    call_count = {"n": 0}

    def _callback(request, context):
        page = call_count["n"]
        call_count["n"] += 1
        return pages[page] if page < len(pages) else []

    return _callback


def test_sync_creates_events_and_bouts(requests_mock):
    requests_mock.get(
        f"{API_BASE}/ufc/events/upcoming",
        json=paginated_events_callback([[make_event_payload()]]),
    )
    requests_mock.get(f"{API_BASE}/ufc/events/evt-1/bouts", json=[make_bout_payload()])

    call_command("sync_upcoming_events")

    assert Event.objects.count() == 1
    assert Bout.objects.count() == 1
    assert Fighter.objects.count() == 2
    event = Event.objects.get()
    assert event.bouts_synced_at is not None


def test_sync_is_idempotent(requests_mock):
    requests_mock.get(
        f"{API_BASE}/ufc/events/upcoming",
        json=paginated_events_callback([[make_event_payload()]]),
    )
    requests_mock.get(f"{API_BASE}/ufc/events/evt-1/bouts", json=[make_bout_payload()])

    call_command("sync_upcoming_events")
    call_command("sync_upcoming_events")

    assert Event.objects.count() == 1
    assert Bout.objects.count() == 1
    assert Fighter.objects.count() == 2


def test_sync_skips_bouts_outside_refresh_window(requests_mock, make_event, make_bout):
    far_out_event = make_event(
        cito_id="evt-far",
        start_time=timezone.now() + timedelta(days=60),
        bouts_synced_at=timezone.now(),
    )
    make_bout(far_out_event, cito_id="existing-bout")

    requests_mock.get(
        f"{API_BASE}/ufc/events/upcoming",
        json=paginated_events_callback([[make_event_payload(event_id="evt-far", days_out=60)]]),
    )
    bouts_mock = requests_mock.get(
        f"{API_BASE}/ufc/events/evt-far/bouts", json=[make_bout_payload()]
    )

    call_command("sync_upcoming_events")

    assert bouts_mock.call_count == 0
    assert Bout.objects.filter(event=far_out_event).count() == 1


def test_sync_respects_max_api_calls_per_run(requests_mock, settings):
    settings.CITO_SYNC_MAX_API_CALLS_PER_RUN = 1

    events = [make_event_payload(event_id=f"evt-{i}", days_out=1) for i in range(3)]
    requests_mock.get(f"{API_BASE}/ufc/events/upcoming", json=paginated_events_callback([events]))
    bouts_mock = requests_mock.get(f"{API_BASE}/ufc/events/evt-0/bouts", json=[make_bout_payload()])

    call_command("sync_upcoming_events")

    assert Event.objects.count() == 3
    assert bouts_mock.call_count == 0


def test_sync_keeps_prior_progress_and_exits_nonzero_on_bout_fetch_failure(requests_mock):
    requests_mock.get(
        f"{API_BASE}/ufc/events/upcoming",
        json=paginated_events_callback(
            [
                [
                    make_event_payload(event_id="evt-ok", days_out=1),
                    make_event_payload(event_id="evt-fail", days_out=2),
                ]
            ]
        ),
    )
    requests_mock.get(f"{API_BASE}/ufc/events/evt-ok/bouts", json=[make_bout_payload()])
    requests_mock.get(f"{API_BASE}/ufc/events/evt-fail/bouts", status_code=500, text="boom")

    with pytest.raises(CommandError):
        call_command("sync_upcoming_events")

    ok_event = Event.objects.get(cito_id="evt-ok")
    fail_event = Event.objects.get(cito_id="evt-fail")
    assert ok_event.bouts_synced_at is not None
    assert Bout.objects.filter(event=ok_event).count() == 1
    assert fail_event.bouts_synced_at is None


def test_sync_raises_on_events_list_fetch_failure(requests_mock):
    requests_mock.get(f"{API_BASE}/ufc/events/upcoming", status_code=500, text="boom")

    with pytest.raises(CommandError):
        call_command("sync_upcoming_events")

    assert Event.objects.count() == 0

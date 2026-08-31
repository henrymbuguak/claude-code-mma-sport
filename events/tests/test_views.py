from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from events.models import Bout, Event

pytestmark = pytest.mark.django_db


def test_anonymous_user_can_view_upcoming_events(client, make_event, make_bout):
    event = make_event(
        name="UFC 999: Test Card",
        venue_name="Test Arena",
        venue_city="Las Vegas",
        start_time=timezone.now() + timedelta(days=10),
    )
    bout = make_bout(event, cito_id="b-1", card_segment=Bout.CardSegment.MAIN_CARD)

    response = client.get(reverse("events:upcoming_list"))

    assert response.status_code == 200
    content = response.content.decode()
    assert "UFC 999: Test Card" in content
    assert "Test Arena" in content
    assert bout.fighter_one.name in content
    assert bout.fighter_two.name in content
    assert f'data-utc="{event.start_time.isoformat()}"' in content


def test_only_upcoming_events_shown_and_ordered(client, make_event):
    completed = make_event(
        cito_id="e-completed",
        status=Event.Status.COMPLETED,
        start_time=timezone.now() - timedelta(days=5),
    )
    later = make_event(cito_id="e-later", start_time=timezone.now() + timedelta(days=30))
    sooner = make_event(cito_id="e-sooner", start_time=timezone.now() + timedelta(days=1))

    response = client.get(reverse("events:upcoming_list"))

    events = list(response.context["events"])
    assert completed not in events
    assert events == [sooner, later]


def test_empty_state_when_no_events(client):
    response = client.get(reverse("events:upcoming_list"))

    assert response.status_code == 200
    assert "No upcoming events scheduled" in response.content.decode()


def test_only_main_card_bouts_shown(client, make_event, make_bout, make_fighter):
    event = make_event()
    main = make_bout(
        event,
        cito_id="b-main",
        card_segment=Bout.CardSegment.MAIN_CARD,
        fighter_one=make_fighter(cito_id="main-f1", name="Main Carder"),
    )
    prelim = make_bout(
        event,
        cito_id="b-prelim",
        card_segment=Bout.CardSegment.PRELIMS,
        fighter_one=make_fighter(cito_id="prelim-f1", name="Prelim Fighter"),
    )

    response = client.get(reverse("events:upcoming_list"))
    content = response.content.decode()

    assert main.fighter_one.name in content
    assert prelim.fighter_one.name not in content


def test_upcoming_list_links_to_event_detail(client, make_event):
    event = make_event()

    response = client.get(reverse("events:upcoming_list"))

    detail_url = reverse("events:event_detail", args=[event.slug])
    assert f'href="{detail_url}"' in response.content.decode()


def test_event_detail_shows_full_card_grouped_by_segment(
    client, make_event, make_bout, make_fighter
):
    event = make_event(name="UFC 999: Full Card")
    main = make_bout(
        event,
        cito_id="b-main",
        card_segment=Bout.CardSegment.MAIN_CARD,
        bout_order=1,
        fighter_one=make_fighter(cito_id="main-f1", name="Main Carder"),
    )
    prelim = make_bout(
        event,
        cito_id="b-prelim",
        card_segment=Bout.CardSegment.PRELIMS,
        bout_order=2,
        fighter_one=make_fighter(cito_id="prelim-f1", name="Prelim Fighter"),
    )
    early = make_bout(
        event,
        cito_id="b-early",
        card_segment=Bout.CardSegment.EARLY_PRELIMS,
        bout_order=3,
        fighter_one=make_fighter(cito_id="early-f1", name="Early Fighter"),
    )

    response = client.get(reverse("events:event_detail", args=[event.slug]))
    content = response.content.decode()

    assert response.status_code == 200
    assert "Main Card" in content
    assert "Preliminary Card" in content
    assert "Early Prelims" in content
    assert main.fighter_one.name in content
    assert prelim.fighter_one.name in content
    assert early.fighter_one.name in content


def test_event_detail_404_for_unknown_slug(client):
    response = client.get(reverse("events:event_detail", args=["no-such-event"]))

    assert response.status_code == 404


def test_event_detail_shows_message_when_no_bouts(client, make_event):
    event = make_event()

    response = client.get(reverse("events:event_detail", args=[event.slug]))

    assert "Fight card not yet announced" in response.content.decode()


def test_event_detail_poster_image_shown_when_set(client, make_event):
    event = make_event(poster_image_url="https://example.com/poster.jpg")

    response = client.get(reverse("events:event_detail", args=[event.slug]))

    assert 'src="https://example.com/poster.jpg"' in response.content.decode()


def test_event_detail_poster_image_omitted_when_not_set(client, make_event):
    event = make_event()

    response = client.get(reverse("events:event_detail", args=[event.slug]))

    assert "event-poster" not in response.content.decode()


def test_event_detail_viewable_for_completed_event_with_status_badge(client, make_event):
    event = make_event(
        status=Event.Status.COMPLETED,
        start_time=timezone.now() - timedelta(days=1),
    )

    response = client.get(reverse("events:event_detail", args=[event.slug]))

    assert response.status_code == 200
    assert "Completed" in response.content.decode()


def test_fighter_profile_shows_info(client, make_fighter):
    fighter = make_fighter(
        name="Jane Doe",
        nickname="The Hammer",
        record="12-1-0 (W-L-D)",
        country="Canada",
        photo_url="https://example.com/jane.jpg",
    )

    response = client.get(reverse("events:fighter_detail", args=[fighter.slug]))
    content = response.content.decode()

    assert response.status_code == 200
    assert "Jane Doe" in content
    assert "The Hammer" in content
    assert "12-1-0 (W-L-D)" in content
    assert "Canada" in content
    assert 'src="https://example.com/jane.jpg"' in content


def test_fighter_profile_omits_photo_and_nickname_when_not_set(client, make_fighter):
    fighter = make_fighter(name="Jane Doe")

    response = client.get(reverse("events:fighter_detail", args=[fighter.slug]))
    content = response.content.decode()

    assert "fighter-photo" not in content
    assert "fighter-nickname" not in content


def test_fighter_profile_shows_upcoming_bout_with_opponent_and_event_link(
    client, make_event, make_bout, make_fighter
):
    fighter = make_fighter(cito_id="f-jane", name="Jane Doe")
    opponent = make_fighter(cito_id="f-jill", name="Jill Roe")
    event = make_event(name="UFC 999: Test Card")
    make_bout(event, fighter_one=fighter, fighter_two=opponent)

    response = client.get(reverse("events:fighter_detail", args=[fighter.slug]))
    content = response.content.decode()

    assert response.status_code == 200
    assert "Jill Roe" in content
    event_url = reverse("events:event_detail", args=[event.slug])
    assert f'href="{event_url}"' in content
    assert f'data-utc="{event.start_time.isoformat()}"' in content


def test_fighter_profile_only_shows_upcoming_bouts(client, make_event, make_bout, make_fighter):
    fighter = make_fighter(cito_id="f-jane", name="Jane Doe")
    completed_event = make_event(
        cito_id="e-completed",
        status=Event.Status.COMPLETED,
        start_time=timezone.now() - timedelta(days=5),
    )
    make_bout(completed_event, cito_id="b-completed", fighter_one=fighter)

    response = client.get(reverse("events:fighter_detail", args=[fighter.slug]))

    assert response.context["upcoming_bouts"] == []


def test_fighter_profile_resolves_opponent_regardless_of_fighter_slot(
    client, make_event, make_bout, make_fighter
):
    fighter = make_fighter(cito_id="f-jane", name="Jane Doe")
    opponent_a = make_fighter(cito_id="f-anna", name="Anna A")
    opponent_b = make_fighter(cito_id="f-becky", name="Becky B")
    event_a = make_event(cito_id="e-a", start_time=timezone.now() + timedelta(days=5))
    event_b = make_event(cito_id="e-b", start_time=timezone.now() + timedelta(days=10))
    make_bout(event_a, cito_id="b-a", fighter_one=fighter, fighter_two=opponent_a)
    make_bout(event_b, cito_id="b-b", fighter_one=opponent_b, fighter_two=fighter)

    response = client.get(reverse("events:fighter_detail", args=[fighter.slug]))
    opponents = [bout.opponent.name for bout in response.context["upcoming_bouts"]]

    assert opponents == ["Anna A", "Becky B"]


def test_fighter_profile_empty_state_when_no_upcoming_bouts(client, make_fighter):
    fighter = make_fighter()

    response = client.get(reverse("events:fighter_detail", args=[fighter.slug]))

    assert "No upcoming bouts scheduled" in response.content.decode()


def test_fighter_profile_404_for_unknown_slug(client):
    response = client.get(reverse("events:fighter_detail", args=["no-such-fighter"]))

    assert response.status_code == 404


def test_upcoming_list_links_fighter_names_to_profile(client, make_event, make_bout):
    event = make_event()
    bout = make_bout(event, card_segment=Bout.CardSegment.MAIN_CARD)

    response = client.get(reverse("events:upcoming_list"))
    content = response.content.decode()

    f1_url = reverse("events:fighter_detail", args=[bout.fighter_one.slug])
    f2_url = reverse("events:fighter_detail", args=[bout.fighter_two.slug])
    assert f'href="{f1_url}"' in content
    assert f'href="{f2_url}"' in content


def test_event_detail_links_fighter_names_to_profile(client, make_event, make_bout):
    event = make_event()
    bout = make_bout(event)

    response = client.get(reverse("events:event_detail", args=[event.slug]))
    content = response.content.decode()

    f1_url = reverse("events:fighter_detail", args=[bout.fighter_one.slug])
    f2_url = reverse("events:fighter_detail", args=[bout.fighter_two.slug])
    assert f'href="{f1_url}"' in content
    assert f'href="{f2_url}"' in content

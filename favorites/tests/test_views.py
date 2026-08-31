from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from events.models import Event
from favorites.models import Follow

pytestmark = pytest.mark.django_db


def test_toggle_creates_follow_for_authenticated_user(client, make_user, make_event):
    user = make_user()
    event = make_event()
    client.force_login(user)

    response = client.post(reverse("favorites:follow_toggle", args=[event.slug]))

    assert response.status_code == 302
    assert response.url == reverse("events:event_detail", args=[event.slug])
    assert Follow.objects.filter(user=user, event=event).exists()


def test_toggle_deletes_follow_on_second_post(client, make_user, make_event):
    user = make_user()
    event = make_event()
    client.force_login(user)

    client.post(reverse("favorites:follow_toggle", args=[event.slug]))
    client.post(reverse("favorites:follow_toggle", args=[event.slug]))

    assert not Follow.objects.filter(user=user, event=event).exists()


def test_toggle_get_is_rejected(client, make_user, make_event):
    user = make_user()
    event = make_event()
    client.force_login(user)

    response = client.get(reverse("favorites:follow_toggle", args=[event.slug]))

    assert response.status_code == 405


def test_toggle_anonymous_post_redirects_to_login(client, make_event):
    event = make_event()

    response = client.post(reverse("favorites:follow_toggle", args=[event.slug]))

    toggle_url = reverse("favorites:follow_toggle", args=[event.slug])
    assert response.status_code == 302
    assert response.url == f"{reverse('accounts:login')}?next={toggle_url}"


def test_my_events_shows_only_own_upcoming_follows(client, make_user, make_event):
    user = make_user(username="alice")
    other_user = make_user(username="bob")

    upcoming = make_event(cito_id="e-upcoming", start_time=timezone.now() + timedelta(days=5))
    completed = make_event(
        cito_id="e-completed",
        status=Event.Status.COMPLETED,
        start_time=timezone.now() - timedelta(days=5),
    )
    others_event = make_event(cito_id="e-others", start_time=timezone.now() + timedelta(days=3))

    Follow.objects.create(user=user, event=upcoming)
    Follow.objects.create(user=user, event=completed)
    Follow.objects.create(user=other_user, event=others_event)

    client.force_login(user)
    response = client.get(reverse("favorites:my_events"))

    assert list(response.context["events"]) == [upcoming]


def test_my_events_empty_state(client, make_user):
    user = make_user()
    client.force_login(user)

    response = client.get(reverse("favorites:my_events"))

    assert "not following any upcoming events" in response.content.decode()


def test_my_events_anonymous_redirects_to_login(client):
    response = client.get(reverse("favorites:my_events"))

    assert response.status_code == 302
    assert response.url == f"{reverse('accounts:login')}?next={reverse('favorites:my_events')}"


def test_event_detail_shows_follow_button_for_non_follower(client, make_user, make_event):
    user = make_user()
    event = make_event()
    client.force_login(user)

    response = client.get(reverse("events:event_detail", args=[event.slug]))
    content = response.content.decode()

    assert ">Follow<" in content
    assert ">Unfollow<" not in content


def test_event_detail_shows_unfollow_button_for_follower(client, make_user, make_event):
    user = make_user()
    event = make_event()
    Follow.objects.create(user=user, event=event)
    client.force_login(user)

    response = client.get(reverse("events:event_detail", args=[event.slug]))
    content = response.content.decode()

    assert ">Unfollow<" in content


def test_event_detail_shows_login_link_for_anonymous_user(client, make_event):
    event = make_event()

    response = client.get(reverse("events:event_detail", args=[event.slug]))
    content = response.content.decode()

    assert "Log in to follow this event" in content
    assert ">Follow<" not in content

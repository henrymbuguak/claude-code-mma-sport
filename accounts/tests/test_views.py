import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_signup_creates_user_and_logs_in(client):
    response = client.post(
        reverse("accounts:signup"),
        {"username": "newuser", "password1": "Sup3r-Secret-Pw!", "password2": "Sup3r-Secret-Pw!"},
    )

    assert response.status_code == 302
    assert response.url == reverse("events:upcoming_list")
    follow = client.get(reverse("events:upcoming_list"))
    assert follow.context["user"].is_authenticated
    assert follow.context["user"].username == "newuser"


def test_signup_duplicate_username_shows_error_and_does_not_create_second_user(
    client, make_user, django_user_model
):
    make_user(username="taken")

    response = client.post(
        reverse("accounts:signup"),
        {"username": "taken", "password1": "Sup3r-Secret-Pw!", "password2": "Sup3r-Secret-Pw!"},
    )

    assert response.status_code == 200
    assert "already exists" in response.content.decode()
    assert django_user_model.objects.filter(username="taken").count() == 1


def test_login_valid_credentials_succeeds(client, make_user):
    make_user(username="alice", password="Correct-Horse-1")

    response = client.post(
        reverse("accounts:login"), {"username": "alice", "password": "Correct-Horse-1"}
    )

    assert response.status_code == 302
    assert response.url == reverse("events:upcoming_list")


def test_login_invalid_credentials_shows_error_and_does_not_log_in(client, make_user):
    make_user(username="alice", password="Correct-Horse-1")

    response = client.post(
        reverse("accounts:login"), {"username": "alice", "password": "wrong-password"}
    )

    assert response.status_code == 200
    assert not response.wsgi_request.user.is_authenticated


def test_logout_post_logs_out_and_redirects(client, make_user):
    user = make_user(username="alice", password="Correct-Horse-1")
    client.force_login(user)

    response = client.post(reverse("accounts:logout"))

    assert response.status_code == 302
    assert response.url == reverse("events:upcoming_list")
    assert not client.get(reverse("events:upcoming_list")).context["user"].is_authenticated


def test_logout_get_is_rejected(client, make_user):
    user = make_user()
    client.force_login(user)

    response = client.get(reverse("accounts:logout"))

    assert response.status_code == 405


def test_nav_shows_login_signup_links_for_anonymous_user(client):
    response = client.get(reverse("events:upcoming_list"))

    content = response.content.decode()
    assert reverse("accounts:login") in content
    assert reverse("accounts:signup") in content


def test_nav_shows_username_and_logout_form_for_authenticated_user(client, make_user):
    user = make_user(username="alice")
    client.force_login(user)

    response = client.get(reverse("events:upcoming_list"))

    content = response.content.decode()
    assert "alice" in content
    assert f'action="{reverse("accounts:logout")}"' in content


def test_anonymous_browsing_still_works_without_login(client):
    """Regression guard for CLAUDE.md: accounts must not gate core browsing."""
    response = client.get(reverse("events:upcoming_list"))

    assert response.status_code == 200

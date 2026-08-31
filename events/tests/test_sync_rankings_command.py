import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from events.models import Fighter, Ranking

pytestmark = pytest.mark.django_db

API_BASE = "https://api.test.local"


@pytest.fixture(autouse=True)
def cito_settings(settings):
    settings.CITO_API_BASE_URL = API_BASE
    settings.CITO_API_KEY = "test-key"


def champion_row():
    return {
        "division": "Bantamweight",
        "rank": None,
        "rankText": "C",
        "fighterSlug": "petr-yan",
        "fighterName": "Petr Yan",
        "isChampion": True,
        "championStatus": "champion",
        "country": "Russia",
        "fighter": {
            "nickname": "No Mercy",
            "record": {"text": "20-5-0 (W-L-D)"},
            "country": "Russia",
            "headshotUrl": "https://example.com/yan.png",
        },
    }


def contender_row():
    return {
        "division": "Bantamweight",
        "rank": 1,
        "rankText": "1",
        "fighterSlug": "merab-dvalishvili",
        "fighterName": "Merab Dvalishvili",
        "isChampion": False,
        "championStatus": "none",
        "country": "Georgia",
        "fighter": {
            "nickname": "The Machine",
            "record": {"text": "19-4-0 (W-L-D)"},
            "country": "Georgia",
            "headshotUrl": "https://example.com/dvalishvili.png",
        },
    }


def test_sync_creates_rankings_and_placeholder_fighters(requests_mock):
    requests_mock.get(
        f"{API_BASE}/ufc/rankings",
        json={"success": True, "data": [champion_row(), contender_row()]},
    )

    call_command("sync_rankings")

    assert Ranking.objects.count() == 2
    assert Fighter.objects.filter(cito_id="petr-yan").exists()
    assert Fighter.objects.filter(cito_id="merab-dvalishvili").exists()

    champion = Ranking.objects.get(fighter__cito_id="petr-yan")
    assert champion.rank is None
    assert champion.is_champion is True
    assert champion.rank_text == "C"

    contender = Ranking.objects.get(fighter__cito_id="merab-dvalishvili")
    assert contender.rank == 1
    assert contender.is_champion is False


def test_sync_handles_explicit_null_nickname_country_and_photo(requests_mock):
    row = {
        "division": "Flyweight",
        "rank": 5,
        "rankText": "5",
        "fighterSlug": "sparse-fighter",
        "fighterName": "Sparse Fighter",
        "isChampion": False,
        "championStatus": "none",
        "country": None,
        "fighter": {"nickname": None, "record": None, "country": None, "headshotUrl": None},
    }
    requests_mock.get(f"{API_BASE}/ufc/rankings", json={"success": True, "data": [row]})

    call_command("sync_rankings")

    fighter = Fighter.objects.get(cito_id="sparse-fighter")
    assert fighter.nickname == ""
    assert fighter.country == ""
    assert fighter.photo_url == ""
    assert fighter.record == ""


def test_sync_rankings_is_idempotent(requests_mock):
    requests_mock.get(
        f"{API_BASE}/ufc/rankings",
        json={"success": True, "data": [champion_row(), contender_row()]},
    )

    call_command("sync_rankings")
    call_command("sync_rankings")

    assert Ranking.objects.count() == 2
    assert Fighter.objects.count() == 2


def test_sync_rankings_does_not_overwrite_existing_fighter_fields(requests_mock, make_fighter):
    existing = make_fighter(cito_id="petr-yan", name="Petr Yan (custom)", record="19-5-0")
    requests_mock.get(f"{API_BASE}/ufc/rankings", json={"success": True, "data": [champion_row()]})

    call_command("sync_rankings")

    existing.refresh_from_db()
    assert existing.name == "Petr Yan (custom)"
    assert existing.record == "19-5-0"


def test_sync_rankings_makes_exactly_one_call(requests_mock):
    # This endpoint doesn't support real pagination (confirmed via a live
    # call), so the sync should always be a single request regardless of
    # how many rows come back.
    mock = requests_mock.get(
        f"{API_BASE}/ufc/rankings",
        json={"success": True, "data": [champion_row(), contender_row()]},
    )

    call_command("sync_rankings")

    assert mock.call_count == 1
    assert Ranking.objects.count() == 2


def test_sync_rankings_skips_fetch_when_budget_already_exhausted(requests_mock, settings):
    settings.CITO_RANKINGS_SYNC_MAX_API_CALLS_PER_RUN = 0
    mock = requests_mock.get(
        f"{API_BASE}/ufc/rankings", json={"success": True, "data": [champion_row()]}
    )

    call_command("sync_rankings")

    assert mock.call_count == 0
    assert Ranking.objects.count() == 0


def test_sync_rankings_raises_on_fetch_failure(requests_mock):
    requests_mock.get(f"{API_BASE}/ufc/rankings", status_code=500, text="boom")

    with pytest.raises(CommandError):
        call_command("sync_rankings")

    assert Ranking.objects.count() == 0

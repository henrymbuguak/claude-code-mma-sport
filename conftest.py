from datetime import timedelta

import pytest
from django.utils import timezone

from events.models import Bout, Event, Fighter, Ranking
from intelligence.models import MatchAnalysis


@pytest.fixture
def make_user(django_user_model):
    def _make(username="alice", password="Sup3r-Secret-Pw!", **kwargs):
        return django_user_model.objects.create_user(username=username, password=password, **kwargs)

    return _make


@pytest.fixture
def make_fighter():
    def _make(cito_id="fighter-1", name="Jane Doe", **kwargs):
        return Fighter.objects.create(cito_id=cito_id, slug=cito_id, name=name, **kwargs)

    return _make


@pytest.fixture
def make_event():
    def _make(cito_id="event-1", name="UFC 999", start_time=None, **kwargs):
        return Event.objects.create(
            cito_id=cito_id,
            slug=cito_id,
            name=name,
            start_time=start_time or timezone.now() + timedelta(days=7),
            **kwargs,
        )

    return _make


@pytest.fixture
def make_bout(make_fighter):
    def _make(event, cito_id="bout-1", fighter_one=None, fighter_two=None, **kwargs):
        fighter_one = fighter_one or make_fighter(cito_id=f"{cito_id}-f1", name="Fighter One")
        fighter_two = fighter_two or make_fighter(cito_id=f"{cito_id}-f2", name="Fighter Two")
        return Bout.objects.create(
            cito_id=cito_id,
            event=event,
            fighter_one=fighter_one,
            fighter_two=fighter_two,
            **kwargs,
        )

    return _make


@pytest.fixture
def make_ranking():
    def _make(fighter, division="Lightweight", **kwargs):
        return Ranking.objects.create(fighter=fighter, division=division, **kwargs)

    return _make


@pytest.fixture
def make_match_analysis():
    def _make(bout, analysis_text="Both fighters bring solid records into this matchup.", **kwargs):
        return MatchAnalysis.objects.create(
            bout=bout, analysis_text=analysis_text, model_used="claude-opus-5", **kwargs
        )

    return _make

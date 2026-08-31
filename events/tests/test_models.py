from datetime import timedelta

import pytest
from django.db import IntegrityError
from django.utils import timezone

from events.models import Bout

pytestmark = pytest.mark.django_db


def test_event_ordering_by_start_time(make_event):
    later = make_event(cito_id="e-later", start_time=timezone.now() + timedelta(days=30))
    sooner = make_event(cito_id="e-sooner", start_time=timezone.now() + timedelta(days=1))

    assert list(type(sooner).objects.all()) == [sooner, later]


def test_event_cito_id_unique(make_event):
    make_event(cito_id="dupe")
    with pytest.raises(IntegrityError):
        make_event(cito_id="dupe")


def test_bout_str_shows_matchup(make_event, make_bout):
    event = make_event()
    bout = make_bout(event)

    assert str(bout) == f"{bout.fighter_one} vs {bout.fighter_two}"


def test_bout_ordering_by_bout_order(make_event, make_bout):
    event = make_event()
    second = make_bout(event, cito_id="b-2", bout_order=2)
    first = make_bout(event, cito_id="b-1", bout_order=1)

    assert list(Bout.objects.filter(event=event)) == [first, second]

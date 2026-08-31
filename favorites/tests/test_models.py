import pytest
from django.db import IntegrityError

from favorites.models import Follow

pytestmark = pytest.mark.django_db


def test_follow_unique_per_user_and_event(make_user, make_event):
    user = make_user()
    event = make_event()
    Follow.objects.create(user=user, event=event)

    with pytest.raises(IntegrityError):
        Follow.objects.create(user=user, event=event)

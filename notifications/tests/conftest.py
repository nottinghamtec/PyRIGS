import datetime

import pytest
from django.utils import timezone

from RIGS.models import Event, Profile


def make_user(username, **kwargs):
    return Profile.objects.create(
        username=username,
        first_name=username.capitalize(),
        email=f"{username}@example.com",
        initials=username[:3].upper(),
        is_active=True,
        is_approved=True,
        **kwargs,
    )


@pytest.fixture
def mic(db):
    return make_user("mic")


@pytest.fixture
def other(db):
    return make_user("other")


@pytest.fixture
def event(mic):
    return Event.objects.create(name="Gig", start_date=timezone.localdate() + datetime.timedelta(days=5), mic=mic)


@pytest.fixture
def push_settings(settings):
    settings.VAPID_PRIVATE_KEY = "private"
    settings.VAPID_PUBLIC_KEY = "public"
    return settings

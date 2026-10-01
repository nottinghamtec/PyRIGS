import importlib
from django.conf import settings
import django
import pytest
from RIGS.models import VatRate
import os

# z3c.rml got ``del importlib.metadata`` in __init__.py
# reinject the original one here to solve ``module 'importlib' has no attribute 'metadata'``
# what a bullsh*t
import importlib.metadata as _importlib_metadata
importlib.metadata = _importlib_metadata


def pytest_configure():
    settings.PASSWORD_HASHERS = (
        'django.contrib.auth.hashers.MD5PasswordHasher',
    )
    settings.WHITENOISE_USE_FINDERS = True
    settings.WHITENOISE_AUTOREFRESH = True
    # TODO Why do we need this, with the above options enabled?
    settings.STATICFILES_DIRS += [
        os.path.join(settings.BASE_DIR, 'static/'),
    ]
    django.setup()


@pytest.fixture  # Overrides the one from pytest-django
def admin_user(admin_user):
    admin_user.username = "EventTest"
    admin_user.first_name = "Event"
    admin_user.last_name = "Test"
    admin_user.initials = "ETU"
    admin_user.is_approved = True
    admin_user.is_supervisor = True
    admin_user.save()
    return admin_user


@pytest.fixture(autouse=True)  # Also enables DB access for all tests as a useful side effect
def vat_rate(db):
    vat_rate = VatRate.objects.create(start_at='2014-03-05', rate=0.20, comment='test1')
    yield vat_rate
    vat_rate.delete()


def _has_transactional_marker(item):
    db_marker = item.get_closest_marker("django_db")
    if db_marker and db_marker.kwargs.get("transaction"):
        return 1
    return 0


def pytest_collection_modifyitems(items):
    items.sort(key=_has_transactional_marker)

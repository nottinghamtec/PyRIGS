from django.conf import settings
import django
import pytest
from django.core.management import call_command
from RIGS.models import VatRate
import random
from django.db import connection


def pytest_configure():
    settings.PASSWORD_HASHERS = (
        'django.contrib.auth.hashers.MD5PasswordHasher',
    )
    settings.WHITENOISE_USE_FINDERS = True
    settings.WHITENOISE_AUTOREFRESH = True
    django.setup()


@pytest.fixture(scope='session')
def splinter_webdriver():
    return 'chrome'


@pytest.fixture(scope='session')
def splinter_screenshot_dir():
    return 'screenshots/'


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

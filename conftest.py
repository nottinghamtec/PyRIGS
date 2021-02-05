from django.conf import settings
import django
import pytest


def pytest_configure():
    settings.PASSWORD_HASHERS = (
        'django.contrib.auth.hashers.MD5PasswordHasher',
    )
    settings.STATICFILES_DIRS.append('static/')  # FIXME
    django.setup()


@pytest.fixture(scope='session')
def splinter_webdriver():
    """Override splinter webdriver name."""
    return 'chrome'


@pytest.fixture(scope='session')
def splinter_screenshot_dir():
    return 'screenshots/'


def _has_transactional_marker(item):
    db_marker = item.get_closest_marker("django_db")
    if db_marker and db_marker.kwargs.get("transaction"):
        return 1
    return 0


def pytest_collection_modifyitems(items):  # Always run database-mulching tests last
    items.sort(key=_has_transactional_marker)

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

from django.conf import settings
import django
import pytest
from django.core.management import call_command
from RIGS.models import VatRate
from PyRIGS.tests import pages
import os
from selenium import webdriver


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


@pytest.fixture
def logged_in_browser(live_server, admin_user, browser, db):
    login_page = pages.LoginPage(browser.driver, live_server.url).open()
    login_page.login(admin_user.username, "password")
    yield browser


@pytest.fixture(scope='session')
def splinter_driver_kwargs():
    options = webdriver.ChromeOptions()
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--headless")
    if settings.CI:
        options.add_argument("--no-sandbox")
    return {"options": options}


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

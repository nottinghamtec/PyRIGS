import os
import pathlib
import sys
from datetime import datetime

import pytz
from django.conf import settings
from django.test import LiveServerTestCase
from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait

from RIGS import models as rigsmodels
from . import pages

from pytest_django.asserts import assertContains


def create_datetime(year, month, day, hour, minute):
    tz = pytz.timezone(settings.TIME_ZONE)
    return tz.localize(datetime(year, month, day, hour, minute)).astimezone(tz)


def create_browser():
    options = webdriver.ChromeOptions()
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--headless")
    if settings.CI:
        options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(options=options)
    return driver


class BaseTest(LiveServerTestCase):
    def setUp(self):
        super().setUpClass()
        self.driver = create_browser()
        self.wait = WebDriverWait(self.driver, 15)

    def tearDown(self):
        super().tearDown()
        self.driver.quit()


class AutoLoginTest(BaseTest):
    def setUp(self):
        super().setUp()
        self.profile = rigsmodels.Profile(
            username="EventTest", first_name="Event", last_name="Test", initials="ETU", is_superuser=True)
        self.profile.set_password("EventTestPassword")
        self.profile.save()
        login_page = pages.LoginPage(self.driver, self.live_server_url).open()
        login_page.login("EventTest", "EventTestPassword")


# FIXME Refactor as a pytest fixture
def screenshot_failure(func):
    def wrapper_func(self, *args, **kwargs):
        try:
            func(self, *args, **kwargs)
        except Exception as e:
            screenshot_name = func.__module__ + "." + func.__qualname__
            screenshot_file = "screenshots/" + func.__qualname__ + ".png"
            if not pathlib.Path("screenshots").is_dir():
                os.mkdir("screenshots")
            self.driver.save_screenshot(screenshot_file)
            print(f"Error in test {screenshot_name} is at path {screenshot_file}", file=sys.stderr)
            raise e

    return wrapper_func


def screenshot_failure_cls(cls):
    for attr in cls.__dict__:
        if callable(getattr(cls, attr)) and attr.startswith("test"):
            setattr(cls, attr, screenshot_failure(getattr(cls, attr)))
    return cls


def assert_times_almost_equal(first_time, second_time):
    assert first_time.replace(microsecond=0, second=0) == second_time.replace(microsecond=0, second=0)


def assert_oembed(alt_event_embed_url, alt_oembed_url, client, event_embed_url, event_url, oembed_url):
    # Test the meta tag is in place
    response = client.get(event_url, follow=True, HTTP_HOST='example.com')
    assertContains(response, 'application/json+oembed')
    assertContains(response, oembed_url)
    # Test that the JSON exists
    response = client.get(oembed_url, follow=True, HTTP_HOST='example.com')
    assert response.status_code == 200
    assertContains(response, event_embed_url)
    # Should also work for non-existant events
    response = client.get(alt_oembed_url, follow=True, HTTP_HOST='example.com')
    assert response.status_code == 200
    assertContains(response, alt_event_embed_url)


def login(client, django_user_model):
    pwd = 'testuser'
    usr = 'TestUser'
    user = django_user_model.objects.create_user(username=usr, email="TestUser@test.com", password=pwd,
                                                 is_superuser=True,
                                                 is_active=True, is_staff=True)
    assert client.login(username=usr, password=pwd)
    return user

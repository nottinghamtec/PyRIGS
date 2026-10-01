from datetime import datetime

import pytz
from django.conf import settings
from selenium import webdriver

from pytest_django.asserts import assertContains


def create_datetime(year, month, day, hour, minute):
    tz = pytz.timezone(settings.TIME_ZONE)
    return tz.localize(datetime(year, month, day, hour, minute)).astimezone(tz)


def create_browser():
    options = webdriver.ChromeOptions()
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--lang=en-GB")
    options.add_argument("--headless")
    if settings.CI:
        options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(options=options)
    return driver


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

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
from envparse import env


def create_datetime(year, month, day, hour, min):
    tz = pytz.timezone(settings.TIME_ZONE)
    return tz.localize(datetime(year, month, day, hour, min)).astimezone(pytz.utc)


def create_browser():
    browser = env('BROWSER', default="chrome")
    if browser == "firefox":
        options = webdriver.FirefoxOptions()
        options.headless = True
        driver = webdriver.Firefox(options=options)
        driver.set_window_position(0, 0)
        # Firefox is pissy about out of bounds otherwise
        driver.set_window_size(3840, 2160)
    else:
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
            print("Error in test {} is at path {}".format(screenshot_name, screenshot_file), file=sys.stderr)
            raise e

    return wrapper_func


def screenshot_failure_cls(cls):
    for attr in cls.__dict__:
        if callable(getattr(cls, attr)) and attr.startswith("test"):
            setattr(cls, attr, screenshot_failure(getattr(cls, attr)))
    return cls


def assert_times_equal(first_time, second_time):
    assert first_time.replace(microsecond=0, second=0) == second_time.replace(microsecond=0, second=0)

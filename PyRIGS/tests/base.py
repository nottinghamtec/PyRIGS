from django.test import LiveServerTestCase
from selenium import webdriver
from RIGS import models as rigsmodels
from . import pages
import os
import pytz
from datetime import date, time, datetime, timedelta
from django.conf import settings
import imgurpython
import PyRIGS.settings
import sys
import pathlib
import inspect


def create_datetime(year, month, day, hour, min):
    tz = pytz.timezone(settings.TIME_ZONE)
    return tz.localize(datetime(year, month, day, hour, min)).astimezone(pytz.utc)


def create_browser():
    options = webdriver.ChromeOptions()
    options.add_argument("--window-size=1920,1080")
    # No caching, please and thank you
    options.add_argument("--aggressive-cache-discard")
    options.add_argument("--disk-cache-size=0")
    if os.environ.get('CI', False):
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(options=options)
    return driver


class BaseTest(LiveServerTestCase):
    def setUp(self):
        super().setUpClass()
        self.driver = create_browser()

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
        loginPage = pages.LoginPage(self.driver, self.live_server_url).open()
        loginPage.login("EventTest", "EventTestPassword")


def screenshot_failure(func):
    def wrapper_func(self, *args, **kwargs):
        try:
            func(self, *args, **kwargs)
        except Exception as e:
            screenshot_name = func.__module__ + "." + func.__qualname__
            screenshot_file = "screenshots/"+func.__qualname__+".png"
            if not pathlib.Path("screenshots").is_dir():
                os.mkdir("screenshots")
            self.driver.save_screenshot(screenshot_file)

            if settings.IMGUR_UPLOAD_CLIENT_ID != "":
                config = {
                    'album': None,
                    'name': screenshot_name,
                    'title': screenshot_name,
                    'description': ""
                }
                client = imgurpython.ImgurClient(settings.IMGUR_UPLOAD_CLIENT_ID, settings.IMGUR_UPLOAD_CLIENT_SECRET)
                image = client.upload_from_path(screenshot_file, config=config)
                print("Error in test {} is at url {}".format(screenshot_name, image['link']), file=sys.stderr)
            else:
                print("Error in test {} is at path {}".format(screenshot_name, screenshot_file), file=sys.stderr)
            raise e
    return wrapper_func


def screenshot_failure_cls(cls):
    for attr in cls.__dict__:
        if callable(getattr(cls, attr)) and attr.startswith("test"):
            setattr(cls, attr, screenshot_failure(getattr(cls, attr)))
    return cls


# Checks if animation is done
class animation_is_finished(object):
    def __init__(self):
        pass

    def __call__(self, driver):
        numberAnimating = driver.execute_script('return $(":animated").length')
        finished = numberAnimating == 0
        if finished:
            import time
            time.sleep(0.1)
        return finished

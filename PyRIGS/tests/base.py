from django.test import LiveServerTestCase
from selenium import webdriver
from RIGS import models as rigsmodels
from . import pages
import os


def create_browser():
    options = webdriver.ChromeOptions()
    options.add_argument("--window-size=1920,1080")
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

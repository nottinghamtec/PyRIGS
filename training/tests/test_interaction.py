import datetime
import time

from django.utils import timezone
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

from PyRIGS.tests.base import AutoLoginTest, screenshot_failure_cls, assert_times_almost_equal
from PyRIGS.tests.pages import animation_is_finished
from training import models
from training.tests import pages


def select_super(page, supervisor):
    page.supervisor_selector.toggle()
    assert page.supervisor_selector.is_open
    page.supervisor_selector.search(supervisor.name[:-6])
    time.sleep(2)  # Slow down for javascript
    assert page.supervisor_selector.options[0].selected
    page.supervisor_selector.toggle()


def test_add_qualification(logged_in_browser, live_server, trainee, supervisor, training_item):
    page = pages.AddQualification(logged_in_browser.driver, live_server.url, pk=trainee.pk).open()
    # assert page.name in str(trainee)

    page.depth = "Training Started"
    page.date = date = datetime.date(1984, 1, 1)
    page.notes = "A note"

    time.sleep(2)  # Slow down for javascript

    page.item_selector.toggle()
    assert page.item_selector.is_open
    page.item_selector.search(training_item.description)
    time.sleep(2)  # Slow down for javascript
    # page.item_selector.set_option(training_item.description, True)
    assert page.item_selector.options[0].selected
    page.item_selector.toggle()

    select_super(page, supervisor)

    page.submit()
    assert page.success
    qualification = models.TrainingItemQualification.objects.get(trainee=trainee, item=training_item)
    assert qualification.supervisor_id == supervisor.pk
    assert qualification.date == date
    assert qualification.notes == "A note"
    assert qualification.depth == models.TrainingItemQualification.STARTED


def test_session_log(logged_in_browser, live_server, trainee, supervisor, training_item, training_item_2):
    page = pages.SessionLog(logged_in_browser.driver, live_server.url).open()

    page.date = date = datetime.date(2001, 1, 10)
    page.notes = note = "A general note"

    time.sleep(2)  # Slow down for javascript

    select_super(page, supervisor)

    page.trainees_selector.toggle()
    assert page.trainees_selector.is_open
    page.trainees_selector.search(trainee.first_name)
    time.sleep(2)  # Slow down for javascript
    page.trainees_selector.set_option(trainee.name, True)
    # assert page.trainees_selector.options[0].selected
    page.trainees_selector.toggle()

    page.training_started_selector.toggle()
    assert page.training_started_selector.is_open
    page.training_started_selector.search(training_item.description[:-2])
    time.sleep(2)  # Slow down for javascript
    # assert page.training_started_selector.options[0].selected
    page.training_started_selector.toggle()

    page.submit()
    assert page.success

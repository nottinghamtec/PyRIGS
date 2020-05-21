from . import pages
from django.core.management import call_command
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse
from urllib.parse import urlparse
from PyRIGS.tests.base import BaseTest, AutoLoginTest
from RIGS import models, urls
from reversion import revisions as reversion
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from PyRIGS.tests.base import animation_is_finished
from PyRIGS.tests import base
from RIGS.tests import regions
import datetime
from datetime import date, time, timedelta
from django.utils import timezone
from selenium.webdriver.support.select import Select

class TestRigboard(AutoLoginTest):
    def setUp(self):
        super().setUp()
        client = models.Person.objects.create(name='Rigboard Test Person', email='rigboard@functional.test')
        self.vatrate = models.VatRate.objects.create(start_at='2014-03-05', rate=0.20, comment='test1')
        self.testEvent = models.Event.objects.create(name="TE E1", status=models.Event.PROVISIONAL,
                                                start_date=date.today() + timedelta(days=6),
                                                description="start future no end",
                                                purchase_order='TESTPO',
                                                person=client,
                                                auth_request_by=self.profile,
                                                auth_request_at=base.create_datetime(2015, 0o6, 0o4, 10, 00),
                                                auth_request_to="some@email.address")
        self.testEvent2 = models.Event.objects.create(name="TE E2", status=models.Event.PROVISIONAL,
                                                start_date=date.today() + timedelta(days=8),
                                                description="start future no end, later",
                                                purchase_order='TESTPO',
                                                person=client,
                                                auth_request_by=self.profile,
                                                auth_request_at=base.create_datetime(2015, 0o6, 0o4, 10, 00),
                                                auth_request_to="some@email.address")

        self.page = pages.Rigboard(self.driver, self.live_server_url).open()

    def test_buttons(self):
        header = regions.Header(self.page, self.driver.find_element(By.CSS_SELECTOR, '.navbar'))
        # TODO Switch to checking reversed links (difficult because of arguments)
        header.find_link("Rigboard").click()
        self.assertEqual(
            self.live_server_url + '/rigboard/', self.driver.current_url)
        header.find_link("Archive").click()
        self.assertEqual(
            self.live_server_url + '/event/archive/', self.driver.current_url)
        # TODO - This fails for some reason
        # header.find_link("New").click()
        # self.assertEqual(
        #    self.live_server_url + '/event/create/', self.driver.current_url)

    def test_event_order(self):
        self.assertIn(self.testEvent.start_date.strftime('%a %d/%m/%Y'), self.page.events[0].dates)
        self.assertIn(self.testEvent2.start_date.strftime('%a %d/%m/%Y'), self.page.events[1].dates)

    def test_add_button(self):
        self.page.add()
        self.assertIn('create', self.driver.current_url)
        # Ideally get a response object to assert 200 on


class TestEventCreate(AutoLoginTest):
    def setUp(self):
        super().setUp()
        self.client = models.Person.objects.create(name='Creation Test Person', email='god@functional.test')
        self.vatrate = models.VatRate.objects.create(start_at='2014-03-05', rate=0.20, comment='test1')
        self.page = pages.CreateEvent(self.driver, self.live_server_url).open()
        self.wait = WebDriverWait(self.driver, 5)

    def test_rig_creation(self):
        self.wait.until(animation_is_finished())
        self.assertFalse(self.page.is_expanded)
        self.page.select_event_type("Rig")
        self.wait.until(animation_is_finished())
        self.assertTrue(self.page.is_expanded)

        self.page.person_selector.toggle()
        self.assertTrue(self.page.person_selector.is_open)
        self.page.person_selector.search(self.client.name)
        self.page.person_selector.set_option(self.client.name, True)
        # TODO This should not be necessary, normally closes automatically
        self.page.person_selector.toggle()
        self.assertFalse(self.page.person_selector.is_open)

        self.page.name = "Test Rig"
        self.page.start_date = datetime.date(2015, 1, 1)
        self.page.start_time = datetime.time(10)
        self.page.end_date = datetime.date(2015, 1, 10)
        self.page.access_at = datetime.datetime(2015, 1, 1, 9)
        self.page.dry_hire = True
        self.page.status = "Booked"
        self.page.collected_by = "Fred"
        self.page.po = "1234"
        self.page.notes = "A note!"

        # TODO Test validation with some wrong data
        self.page.submit()
        self.assertTrue(self.page.success)

    # TODO
    def test_modals(self):
        self.wait.until(animation_is_finished())
        self.assertFalse(self.page.is_expanded)
        self.page.select_event_type("Rig")
        self.wait.until(animation_is_finished())
        self.assertTrue(self.page.is_expanded)
        # Create new person
        modal = self.page.add_person()
        # animation_is_finished doesn't work for whatever reason...
        self.wait.until(EC.visibility_of_element_located((By.ID, 'modal')))
        self.assertTrue(modal.is_open)
        self.assertIn("Add Person", modal.header)

        # Fill person form out and submit
        person_name = "Test Person"
        modal.name = person_name
        modal.submit()
        self.wait.until(EC.invisibility_of_element_located((By.ID, 'modal')))
        self.assertFalse(modal.is_open)

        # See new person selected
        select_element = self.driver.find_element(By.ID,'id_person')
        select_object = Select(select_element)

        person1 = models.Person.objects.get(name=person_name)
        self.assertEqual(person1.name, select_object.first_selected_option.text)
        # and backend
        # self.assertEqual(person1.pk, int(self.page.person_selector.get_attribute("value")))

        # Change mind and add another
        self.wait.until(animation_is_finished())
        modal = self.page.add_person()
        self.wait.until(EC.visibility_of_element_located((By.ID, 'modal')))
        self.assertTrue(modal.is_open)
        self.assertIn("Add Person", modal.header)

        person_name = "Test Person 2"
        modal.name = person_name
        modal.submit()
        self.wait.until(EC.invisibility_of_element_located((By.ID, 'modal')))
        self.assertFalse(modal.is_open)

        person2 = models.Person.objects.get(name=person_name)
        options = list((x for x in self.page.person_selector.options if x.selected))
        self.assertTrue(len(options) == 1)
        self.assertEqual(person2.name, options[0].name)
        # and backend
        # self.assertEqual(person1.pk, int(self.page.person_selector.get_attribute("value")))

        # Was right the first time, change it back
        self.page.person_selector.search(person1.name)
        # TODO Check multiple cannot be selected? Is that necessary?
        self.page.person_selector.set_option(person1.name, True)

        options = list((x for x in self.page.person_selector.options if x.selected))
        self.assertTrue(len(options) == 1)
        self.assertEqual(person2.name, options[0].name)
        # and backend
        # self.assertEqual(person1.pk, int(self.page.person_selector.get_attribute("value")))

        pass

        # Edit Person 1 to have a better name
        form.find_element_by_xpath(
            '//a[@data-target="#id_person" and contains(@href, "%s/edit/")]' % person1.pk).click()
        wait.until(animation_is_finished())
        self.assertTrue(modal.is_displayed())
        self.assertIn("Edit Person", modal.find_element_by_tag_name('h3').text)
        name = modal.find_element_by_xpath(
            '//div[@id="modal"]//input[@id="id_name"]')
        self.assertEqual(person1.name, name.get_attribute('value'))
        name.clear()
        name.send_keys('Rig ' + person1.name)
        name.send_keys(Keys.ENTER)

        wait.until(animation_is_finished())

        self.assertFalse(modal.is_displayed())
        person1 = models.Person.objects.get(pk=person1.pk)
        self.assertEqual(person1.name, form.find_element_by_xpath(
            '//button[@data-id="id_person"]/span').text)

        # Create organisation
        wait.until(animation_is_finished())
        add_button = self.browser.find_element_by_xpath(
            '//a[@data-target="#id_organisation" and contains(@href, "add")]')
        add_button.click()
        modal = self.browser.find_element_by_id('modal')
        wait.until(animation_is_finished())
        self.assertTrue(modal.is_displayed())
        self.assertIn("Add Organisation", modal.find_element_by_tag_name('h3').text)
        modal.find_element_by_xpath(
            '//div[@id="modal"]//input[@id="id_name"]').send_keys("Test Organisation")
        modal.find_element_by_xpath(
            '//div[@id="modal"]//input[@type="submit"]').click()

        # See it is selected
        wait.until(animation_is_finished())
        self.assertFalse(modal.is_displayed())
        obj = models.Organisation.objects.get(name="Test Organisation")
        self.assertEqual(obj.name, form.find_element_by_xpath(
            '//button[@data-id="id_organisation"]/span').text)
        # and backend
        option = form.find_element_by_xpath(
            '//select[@id="id_organisation"]//option[@selected="selected"]')
        self.assertEqual(obj.pk, int(option.get_attribute("value")))

        # Create venue
        wait.until(animation_is_finished())
        add_button = self.browser.find_element_by_xpath(
            '//a[@data-target="#id_venue" and contains(@href, "add")]')
        wait.until(animation_is_finished())
        add_button.click()
        wait.until(animation_is_finished())
        modal = self.browser.find_element_by_id('modal')
        wait.until(animation_is_finished())
        self.assertTrue(modal.is_displayed())
        self.assertIn("Add Venue", modal.find_element_by_tag_name('h3').text)
        modal.find_element_by_xpath(
            '//div[@id="modal"]//input[@id="id_name"]').send_keys("Test Venue")
        modal.find_element_by_xpath(
            '//div[@id="modal"]//input[@type="submit"]').click()

        # See it is selected
        wait.until(animation_is_finished())
        self.assertFalse(modal.is_displayed())
        obj = models.Venue.objects.get(name="Test Venue")
        self.assertEqual(obj.name, form.find_element_by_xpath(
            '//button[@data-id="id_venue"]/span').text)
        # and backend
        option = form.find_element_by_xpath(
            '//select[@id="id_venue"]//option[@selected="selected"]')
        self.assertEqual(obj.pk, int(option.get_attribute("value")))

    # TODO Testing of internal rig (approval system interface)

    def test_non_rig_creation(self):
        self.wait.until(animation_is_finished())
        self.assertFalse(self.page.is_expanded)
        self.page.select_event_type("Non-Rig")
        self.wait.until(animation_is_finished())
        self.assertTrue(self.page.is_expanded)

        # self.assertFalse(self.page.person_selector.is_displayed())

    def test_subhire_creation(self):
        pass

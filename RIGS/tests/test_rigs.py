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
from selenium.webdriver.common.action_chains import ActionChains

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

        # TODO

    def test_event_item_creation(self):
        self.wait.until(animation_is_finished())
        self.assertFalse(self.page.is_expanded)
        self.page.select_event_type("Rig")
        self.wait.until(animation_is_finished())
        self.assertTrue(self.page.is_expanded)

        self.page.name = "Test Event with Items"

        self.page.person_selector.toggle()
        self.assertTrue(self.page.person_selector.is_open)
        self.page.person_selector.search(self.client.name)
        self.page.person_selector.set_option(self.client.name, True)
        # TODO This should not be necessary, normally closes automatically
        self.page.person_selector.toggle()
        self.assertFalse(self.page.person_selector.is_open)

        self.page.start_date = datetime.date(1984, 1, 1)

        modal = self.page.add_event_item()
        self.wait.until(animation_is_finished())
        # See modal has opened
        self.assertTrue(modal.is_open)
        self.assertIn("New Event", modal.header)

        modal.name = "Test Item 1"
        modal.description = "This is an item description\nthat for reasons unknown spans two lines"
        modal.quantity = "2"
        modal.price = "23.95"
        modal.submit()
        self.wait.until(animation_is_finished())

        # Confirm item has been saved to json field
        objectitems = self.driver.execute_script("return objectitems;")
        self.assertEqual(1, len(objectitems))
        testitem = objectitems["-1"]['fields']  # as we are deliberately creating this we know the ID
        self.assertEqual("Test Item 1", testitem['name'])
        self.assertEqual("2", testitem['quantity'])  # test a couple of "worse case" fields

        total = self.driver.find_element_by_id('total')
        ActionChains(self.driver).move_to_element(total).perform()

        # See new item appear in table
        row = self.page.item_row("-1")  # ID number is known, see above
        # Scroll into view
        self.assertIn("Test Item 1", row.name)
        self.assertIn("This is an item description",
                      row.description)
        self.assertEqual('23.95', row.price)
        self.assertEqual("2", row.quantity)
        self.assertEqual('47.90', row.subtotal)

        # Check totals TODO convert to page properties
        self.assertEqual("47.90", self.driver.find_element_by_id('sumtotal').text)
        self.assertIn("(TBC)", self.driver.find_element_by_id('vat-rate').text)
        self.assertEqual("9.58", self.driver.find_element_by_id('vat').text)
        self.assertEqual("57.48", total.text)

        self.page.submit()

    # TODO Testing of internal rig (approval system interface)

    def test_non_rig_creation(self):
        self.wait.until(animation_is_finished())
        self.assertFalse(self.page.is_expanded)
        self.page.select_event_type("Non-Rig")
        self.wait.until(animation_is_finished())
        self.assertTrue(self.page.is_expanded)

        self.assertFalse(self.page.person_selector.is_open)

        rig_name = "Test Non-Rig"
        self.page.name = rig_name

        # Double-check we don't lose data when swapping
        self.page.select_event_type("Rig")
        self.wait.until(animation_is_finished())
        self.assertEquals(self.page.name, rig_name)
        self.wait.until(animation_is_finished())
        self.page.select_event_type("Non-Rig")

        self.page.start_date = datetime.date(2020, 1, 1)
        self.page.status = "Confirmed"

        self.page.submit()
        self.assertTrue(self.page.success)

    def test_subhire_creation(self):
        pass

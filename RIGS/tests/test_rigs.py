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
from django.db import transaction


class BaseRigboardTest(AutoLoginTest):
    def setUp(self):
        self.vatrate = models.VatRate.objects.create(start_at='2014-03-05', rate=0.20, comment='test1')
        super().setUp()
        self.client = models.Person.objects.create(name='Rigboard Test Person', email='rigboard@functional.test')
        self.testEvent = models.Event.objects.create(name="TE E1", status=models.Event.PROVISIONAL,
                                                     start_date=date.today() + timedelta(days=6),
                                                     description="start future no end",
                                                     purchase_order='TESTPO',
                                                     person=self.client,
                                                     auth_request_by=self.profile,
                                                     auth_request_at=base.create_datetime(2015, 0o6, 0o4, 10, 00),
                                                     auth_request_to="some@email.address")

        item1 = models.EventItem(
            event=self.testEvent,
            name="Test Item 1",
            cost="10.00",
            quantity="1",
            order=1
        ).save()
        item2 = models.EventItem(
            event=self.testEvent,
            name="Test Item 2",
            description="Foo",
            cost="9.72",
            quantity="3",
            order=2,
        ).save()
        self.wait = WebDriverWait(self.driver, 5)

    def select_event_type(self, event_type):
        self.wait.until(animation_is_finished())
        self.assertFalse(self.page.is_expanded)
        self.page.select_event_type(event_type)
        self.wait.until(animation_is_finished())
        self.assertTrue(self.page.is_expanded)


class TestRigboard(BaseRigboardTest):
    def setUp(self):
        super().setUp()
        self.testEvent2 = models.Event.objects.create(name="TE E2", status=models.Event.PROVISIONAL,
                                                      start_date=date.today() + timedelta(days=8),
                                                      description="start future no end, later",
                                                      purchase_order='TESTPO',
                                                      person=self.client,
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


class TestEventCreate(BaseRigboardTest):
    def setUp(self):
        super().setUp()
        self.page = pages.CreateEvent(self.driver, self.live_server_url).open()

    def test_rig_creation(self):
        self.select_event_type("Rig")

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
        self.select_event_type("Rig")
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
        self.page.person_selector.toggle()
        self.assertEqual(self.page.person_selector.options[0].name, person_name)
        self.page.person_selector.toggle()

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
        self.assertEqual(self.page.person_selector.options[1].name, person_name)

        # TODO

    def test_date_validation(self):
        self.select_event_type("Rig")

        self.page.person_selector.toggle()
        self.assertTrue(self.page.person_selector.is_open)
        self.page.person_selector.search(self.client.name)
        self.page.person_selector.set_option(self.client.name, True)
        # TODO This should not be necessary, normally closes automatically
        self.page.person_selector.toggle()
        self.assertFalse(self.page.person_selector.is_open)

        self.page.name = "Test Date Validation"
        # Both dates, no times, end before start
        self.page.start_date = datetime.date(2020, 1, 10)
        self.page.end_date = datetime.date(2020, 1, 1)
        # Expected to fail
        self.page.submit()
        self.assertFalse(self.page.success)
        self.assertIn("can't finish before it has started", self.page.errors["General form errors"][0])
        self.wait.until(animation_is_finished())

        # end time before start
        self.page.start_date = datetime.date(2020, 1, 1)
        self.page.start_time = datetime.time(10)
        self.page.end_time = datetime.time(9)

        # Expected to fail
        self.page.submit()
        self.assertFalse(self.page.success)
        self.assertIn("can't finish before it has started", self.page.errors["General form errors"][0])

        # Fix it
        self.page.end_time = datetime.time(23)

        # Should work
        self.page.submit()
        self.assertTrue(self.page.success)

    def test_event_item_creation(self):
        self.select_event_type("Rig")

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
        self.select_event_type("Non-Rig")

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


class TestEventDuplicate(BaseRigboardTest):
    def setUp(self):
        super().setUp()
        self.page = pages.DuplicateEvent(self.driver, self.live_server_url, event_id=self.testEvent.pk).open()

    def test_rig_duplicate(self):
        table = self.page.item_table
        self.assertIn("Test Item 1", table.text)
        self.assertIn("Test Item 2", table.text)

        # Check the info message is visible
        self.assertIn("Event data duplicated but not yet saved", self.page.warning)

        modal = self.page.add_event_item()
        self.wait.until(animation_is_finished())
        # See modal has opened
        self.assertTrue(modal.is_open)
        self.assertIn(self.testEvent.name, modal.header)

        modal.name = "Test Item 3"
        modal.description = "This is an item description\nthat for reasons unknown spans two lines"
        modal.quantity = "2"
        modal.price = "23.95"
        modal.submit()
        self.wait.until(animation_is_finished())

        # Attempt to save
        ActionChains(self.driver).move_to_element(table).perform()
        self.page.submit()

        # TODO Rewrite when EventDetail page is implemented
        newEvent = models.Event.objects.latest('pk')

        self.assertEqual(newEvent.auth_request_to, None)
        self.assertEqual(newEvent.auth_request_by, None)
        self.assertEqual(newEvent.auth_request_at, None)

        self.assertFalse(hasattr(newEvent, 'authorised'))

        self.assertNotIn("N%05d" % self.testEvent.pk, self.driver.find_element_by_xpath('//h1').text)
        self.assertNotIn("Event data duplicated but not yet saved", self.page.warning)  # Check info message not visible

        # Check the new items are visible
        table = self.page.item_table
        self.assertIn("Test Item 1", table.text)
        self.assertIn("Test Item 2", table.text)
        self.assertIn("Test Item 3", table.text)

        infoPanel = self.driver.find_element_by_xpath('//div[contains(text(), "Event Info")]/..')
        self.assertIn("N0000%d" % self.testEvent.pk,
                      infoPanel.find_element_by_xpath('//dt[text()="Based On"]/following-sibling::dd[1]').text)
        # Check the PO hasn't carried through
        self.assertNotIn("TESTPO", infoPanel.find_element_by_xpath('//dt[text()="PO"]/following-sibling::dd[1]').text)

        self.assertIn("N%05d" % self.testEvent.pk,
                      infoPanel.find_element_by_xpath('//dt[text()="Based On"]/following-sibling::dd[1]').text)

        self.driver.get(self.live_server_url + '/event/' + str(self.testEvent.pk))  # Go back to the old event

        # Check that based-on hasn't crept into the old event
        infoPanel = self.driver.find_element_by_xpath('//div[contains(text(), "Event Info")]/..')
        self.assertNotIn("N0000%d" % self.testEvent.pk,
                         infoPanel.find_element_by_xpath('//dt[text()="Based On"]/following-sibling::dd[1]').text)
        # Check the PO remains on the old event
        self.assertIn("TESTPO", infoPanel.find_element_by_xpath('//dt[text()="PO"]/following-sibling::dd[1]').text)

        self.assertNotIn("N%05d" % self.testEvent.pk,
                         infoPanel.find_element_by_xpath('//dt[text()="Based On"]/following-sibling::dd[1]').text)

        # Check the items are as they were
        table = self.page.item_table  # ID number is known, see above
        self.assertIn("Test Item 1", table.text)
        self.assertIn("Test Item 2", table.text)
        self.assertNotIn("Test Item 3", table.text)


class TestEventEdit(BaseRigboardTest):
    def setUp(self):
        super().setUp()
        self.page = pages.EditEvent(self.driver, self.live_server_url, event_id=self.testEvent.pk).open()

    def test_rig_edit(self):
        self.page.name = "Edited Event"

        modal = self.page.add_event_item()
        self.wait.until(animation_is_finished())
        # See modal has opened
        self.assertTrue(modal.is_open)
        self.assertIn(self.testEvent.name, modal.header)

        modal.name = "Test Item 3"
        modal.description = "This is an item description\nthat for reasons unknown spans two lines"
        modal.quantity = "2"
        modal.price = "23.95"
        modal.submit()
        self.wait.until(animation_is_finished())

        # Attempt to save
        ActionChains(self.driver).move_to_element(self.page.item_table).perform()
        self.page.submit()

        self.assertTrue(self.page.success)

        self.page = pages.EventDetail(self.driver, self.live_server_url, event_id=self.testEvent.pk).open()
        self.assertIn(self.page.event_name, self.testEvent.name)
        self.assertEqual(self.page.name, self.testEvent.person.name)
        # Check the new items are visible
        table = self.page.item_table
        self.assertIn("Test Item 3", table.text)


class TestEventDetail(BaseRigboardTest):
    def setUp(self):
        super().setUp()
        self.page = pages.EventDetail(self.driver, self.live_server_url, event_id=self.testEvent.pk).open()

    def test_rig_detail(self):
        self.assertIn("N%05d | %s" % (self.testEvent.pk, self.testEvent.name), self.page.event_name)
        self.assertEqual(person.name, self.page.name)
        self.assertEqual(person.email, self.page.email)
        self.assertEqual(person.phone, self.page.phone)

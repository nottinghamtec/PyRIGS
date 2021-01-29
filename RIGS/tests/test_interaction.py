import datetime
from datetime import date, time, timedelta

from django.test.client import Client
from django.utils import timezone
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from PyRIGS.tests import base
from PyRIGS.tests import regions as base_regions
from PyRIGS.tests.base import (AutoLoginTest, screenshot_failure_cls)
from PyRIGS.tests.pages import animation_is_finished
from RIGS import models
from RIGS.tests import regions
from . import pages


@screenshot_failure_cls
class BaseRigboardTest(AutoLoginTest):
    def setUp(self):
        self.vatrate = models.VatRate.objects.create(start_at='2014-03-05', rate=0.20, comment='test1')
        super().setUp()
        self.client = models.Person.objects.create(name='Rigboard Test Person', email='rigboard@functional.test')
        self.wait = WebDriverWait(self.driver, 10)

    def select_event_type(self, event_type):
        self.wait.until(animation_is_finished())
        self.assertFalse(self.page.is_expanded)
        self.page.select_event_type(event_type)
        self.wait.until(animation_is_finished())
        self.assertTrue(self.page.is_expanded)


@screenshot_failure_cls
class TestRigboard(BaseRigboardTest):
    def setUp(self):
        super().setUp()
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


@screenshot_failure_cls
class TestEventCreate(BaseRigboardTest):
    def setUp(self):
        super().setUp()
        self.page = pages.CreateEvent(self.driver, self.live_server_url).open()

    def test_rig_creation(self):
        self.select_event_type("Rig")

        self.page.person_selector.search(self.client.name)
        self.page.person_selector.set_option(self.client.name, True)
        self.page.person_selector.toggle()
        self.assertFalse(self.page.person_selector.is_open)

        self.page.name = "Test Rig"

        # Both dates, no times, end before start
        self.page.start_date = datetime.date(2020, 1, 10)
        self.page.end_date = datetime.date(2020, 1, 1)
        # Expected to fail
        self.page.submit()
        self.assertFalse(self.page.success)
        self.assertIn("Unless you've invented time travel, the event can't finish before it has started.", self.page.errors["End date"])
        self.wait.until(animation_is_finished())

        # Fix it
        self.page.end_date = datetime.date(2020, 1, 11)
        self.page.access_at = datetime.datetime(2020, 1, 1, 9)
        self.page.dry_hire = True
        self.page.status = "Booked"
        self.page.collected_by = "Fred"
        self.page.po = "1234"
        self.page.notes = "A note!"

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
        self.assertIn("Create Person", modal.header)

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
        self.assertIn("Create Person", modal.header)

        person_name = "Test Person 2"
        modal.name = person_name
        modal.submit()
        self.wait.until(EC.invisibility_of_element_located((By.ID, 'modal')))
        self.assertFalse(modal.is_open)
        self.page.person_selector.toggle()
        self.assertEqual(self.page.person_selector.options[0].name, person_name)
        self.page.person_selector.toggle()

        # TODO

    def test_event_item_creation(self):
        self.select_event_type("Rig")

        self.page.name = "Test Event with Items"

        self.page.person_selector.search(self.client.name)
        self.page.person_selector.set_option(self.client.name, True)
        # TODO This should not be necessary, normally closes automatically
        self.page.person_selector.toggle()
        self.assertFalse(self.page.person_selector.is_open)

        # Note to self, don't set dates before 2014, which is the beginning of VAT as far as the tests are concerned...
        self.page.start_date = datetime.date(2084, 1, 1)

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
        self.assertEqual(self.page.name, rig_name)
        self.wait.until(animation_is_finished())
        self.page.select_event_type("Non-Rig")

        self.page.start_date = datetime.date(2020, 1, 1)
        self.page.status = "Confirmed"

        self.page.submit()
        self.assertTrue(self.page.success)


@screenshot_failure_cls
class TestEventDuplicate(BaseRigboardTest):
    def setUp(self):
        super().setUp()
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
        self.page.submit()

        # TODO Rewrite when EventDetail page is implemented
        newEvent = models.Event.objects.latest('pk')

        self.assertEqual(newEvent.auth_request_to, None)
        self.assertEqual(newEvent.auth_request_by, None)
        self.assertEqual(newEvent.auth_request_at, None)

        self.assertFalse(newEvent.authorised)

        self.assertNotIn("N%05d" % self.testEvent.pk, self.driver.find_element_by_xpath('//h1').text)
        self.assertNotIn("Event data duplicated but not yet saved", self.page.warning)  # Check info message not visible

        # Check the new items are visible
        table = self.page.item_table
        self.assertIn("Test Item 1", table.text)
        self.assertIn("Test Item 2", table.text)
        self.assertIn("Test Item 3", table.text)

        infoPanel = self.driver.find_element_by_xpath('//div[contains(text(), "Event Info")]/..')
        self.assertIn("N%05d" % self.testEvent.pk,
                      infoPanel.find_element_by_xpath('//dt[text()="Based On"]/following-sibling::dd[1]').text)
        # Check the PO hasn't carried through
        self.assertNotIn("TESTPO", infoPanel.find_element_by_xpath('//dt[text()="PO"]/following-sibling::dd[1]').text)

        self.assertIn("N%05d" % self.testEvent.pk,
                      infoPanel.find_element_by_xpath('//dt[text()="Based On"]/following-sibling::dd[1]').text)

        self.driver.get(self.live_server_url + '/event/' + str(self.testEvent.pk))  # Go back to the old event

        # Check that based-on hasn't crept into the old event
        infoPanel = self.driver.find_element_by_xpath('//div[contains(text(), "Event Info")]/..')
        self.assertNotIn("N%05d" % self.testEvent.pk,
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


@screenshot_failure_cls
class TestEventEdit(BaseRigboardTest):
    def setUp(self):
        super().setUp()
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
        self.testEvent.refresh_from_db()
        self.assertIn(self.testEvent.name, self.page.event_name)
        self.assertEqual(self.page.name, self.testEvent.person.name)
        # Check the new items are visible
        table = self.page.item_table
        self.assertIn("Test Item 3", table.text)


@screenshot_failure_cls
class TestEventDetail(BaseRigboardTest):
    def setUp(self):
        super().setUp()
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
        self.page = pages.EventDetail(self.driver, self.live_server_url, event_id=self.testEvent.pk).open()

    def test_rig_detail(self):
        self.assertIn("N%05d | %s" % (self.testEvent.pk, self.testEvent.name), self.page.event_name)
        self.assertEqual(self.client.name, self.page.name)
        self.assertEqual(self.client.email, self.page.email)
        self.assertEqual(self.client.phone, None)


@screenshot_failure_cls
class TestCalendar(BaseRigboardTest):
    def setUp(self):
        super().setUp()
        self.all_events = set(range(1, 18))
        self.current_events = (1, 2, 3, 6, 7, 8, 10, 11, 12, 14, 15, 16, 18)
        self.not_current_events = set(self.all_events) - set(self.current_events)

        # produce 7 normal events - 5 current - 1 last week - 1 two years ago - 2 provisional - 2 confirmed - 3 booked
        models.Event.objects.create(name="TE E1", status=models.Event.PROVISIONAL,
                                    start_date=date.today() + timedelta(days=6), description="start future no end")
        models.Event.objects.create(name="TE E2", status=models.Event.PROVISIONAL, start_date=date.today(),
                                    description="start today no end")
        models.Event.objects.create(name="TE E3", status=models.Event.CONFIRMED, start_date=date.today(),
                                    end_date=date.today(), description="start today with end today")
        models.Event.objects.create(name="TE E4", status=models.Event.CONFIRMED,
                                    start_date=date.today() - timedelta(weeks=104),
                                    description="start past 2 years no end")
        models.Event.objects.create(name="TE E5", status=models.Event.BOOKED,
                                    start_date=date.today() - timedelta(days=7),
                                    end_date=date.today() - timedelta(days=1),
                                    description="start past 1 week with end past")
        models.Event.objects.create(name="TE E6", status=models.Event.BOOKED,
                                    start_date=date.today() - timedelta(days=2),
                                    start_time=time(8, 00),
                                    end_date=date.today() + timedelta(days=2),
                                    end_time=time(23, 00), description="start past, end future")
        models.Event.objects.create(name="TE E7", status=models.Event.BOOKED,
                                    start_date=date.today() + timedelta(days=2),
                                    end_date=date.today() + timedelta(days=2), description="start + end in future")

        # 2 cancelled - 1 current
        models.Event.objects.create(name="TE E8", start_date=date.today() + timedelta(days=2),
                                    end_date=date.today() + timedelta(days=2), status=models.Event.CANCELLED,
                                    description="cancelled in future")
        models.Event.objects.create(name="TE E9", start_date=date.today() - timedelta(days=1),
                                    end_date=date.today() + timedelta(days=2), status=models.Event.CANCELLED,
                                    description="cancelled and started")

        # 5 dry hire - 3 current - 1 cancelled
        models.Event.objects.create(name="TE E10", start_date=date.today(), dry_hire=True, description="dryhire today")
        models.Event.objects.create(name="TE E11", start_date=date.today(), dry_hire=True, checked_in_by=self.profile,
                                    description="dryhire today, checked in")
        models.Event.objects.create(name="TE E12", start_date=date.today() - timedelta(days=1), dry_hire=True,
                                    status=models.Event.BOOKED, description="dryhire past")
        models.Event.objects.create(name="TE E13", start_date=date.today() - timedelta(days=2), dry_hire=True,
                                    checked_in_by=self.profile, description="dryhire past checked in")
        models.Event.objects.create(name="TE E14", start_date=date.today(), dry_hire=True,
                                    status=models.Event.CANCELLED, description="dryhire today cancelled")

        # 4 non rig - 3 current
        models.Event.objects.create(name="TE E15", start_date=date.today(), is_rig=False, description="non rig today")
        models.Event.objects.create(name="TE E16", start_date=date.today() + timedelta(days=1), is_rig=False,
                                    description="non rig tomorrow")
        models.Event.objects.create(name="TE E17", start_date=date.today() - timedelta(days=1), is_rig=False,
                                    description="non rig yesterday")
        models.Event.objects.create(name="TE E18", start_date=date.today(), is_rig=False, status=models.Event.CANCELLED,
                                    description="non rig today cancelled")

        self.page = pages.UserPage(self.driver, self.live_server_url).open()

    def test_api_key_generation(self):
        # Completes and comes back to /user/
        # Checks that no api key is displayed
        self.assertEqual("No API Key Generated", self.page.api_key)

        # Now creates an API key, and check a URL is displayed one
        self.page.generate_key()
        self.assertIn("rigs.ics", self.page.cal_url)
        self.assertNotIn("?", self.page.cal_url)

        # Lets change everything so it's not the default value
        self.page.toggle_filter('rig')
        self.page.toggle_filter('non-rig')
        self.page.toggle_filter('dry-hire')
        self.page.toggle_filter('cancelled')
        self.page.toggle_filter('provisional')
        self.page.toggle_filter('confirmed')

        # and then check the url is correct
        self.assertIn(
            "rigs.ics?rig=false&non-rig=false&dry-hire=false&cancelled=true&provisional=false&confirmed=false",
            self.page.cal_url)

        # Awesome - all seems to work

    def test_ics_files(self):
        specialEvent = models.Event.objects.get(name="TE E6")

        # Now creates an API key, and check a URL is displayed one
        self.page.generate_key()

        c = Client()

        # Default settings - should have all non-cancelled events
        # Get the ical file (can't do this in selanium because reasons)
        icalUrl = self.page.cal_url
        response = c.get(self.page.cal_url)
        self.assertEqual(200, response.status_code)

        # content = response.content.decode('utf-8')

        # Check has entire file
        self.assertContains(response, "BEGIN:VCALENDAR")
        self.assertContains(response, "END:VCALENDAR")

        expectedIn = [1, 2, 3, 5, 6, 7, 10, 11, 12, 13, 15, 16, 17]
        for test in range(1, 18):
            if test in expectedIn:
                self.assertContains(response, "TE E" + str(test) + " ")
            else:
                self.assertNotContains(response, "TE E" + str(test) + " ")

        # Check that times have been included correctly
        self.assertContains(response,
                            specialEvent.start_date.strftime('%Y%m%d') + 'T' + specialEvent.start_time.strftime(
                                '%H%M%S'))
        self.assertContains(response,
                            specialEvent.end_date.strftime('%Y%m%d'))
        self.assertContains(response,
                            specialEvent.end_time.strftime('%H%M%S'))

        # Only non rigs
        self.page.toggle_filter('rig')
        self.page.toggle_filter('non-rig')

        icalUrl = self.page.cal_url
        response = c.get(icalUrl)
        self.assertEqual(200, response.status_code)

        expectedIn = [10, 11, 12, 13]
        for test in range(1, 18):
            if test in expectedIn:
                self.assertContains(response, "TE E" + str(test) + " ")
            else:
                self.assertNotContains(response, "TE E" + str(test) + " ")

        # Only provisional rigs
        self.page.toggle_filter('rig')
        self.page.toggle_filter('dry-hire')
        self.page.toggle_filter('confirmed')

        icalUrl = self.page.cal_url
        response = c.get(icalUrl)
        self.assertEqual(200, response.status_code)

        expectedIn = [1, 2]
        for test in range(1, 18):
            if test in expectedIn:
                self.assertContains(response, "TE E" + str(test) + " ")
            else:
                self.assertNotContains(response, "TE E" + str(test) + " ")

        # Only cancelled non-rigs
        self.page.toggle_filter('rig')
        self.page.toggle_filter('non-rig')
        self.page.toggle_filter('provisional')
        self.page.toggle_filter('cancelled')

        icalUrl = self.page.cal_url
        response = c.get(icalUrl)
        self.assertEqual(200, response.status_code)

        expectedIn = [18]
        for test in range(1, 18):
            if test in expectedIn:
                self.assertContains(response, "TE E" + str(test) + " ")
            else:
                self.assertNotContains(response, "TE E" + str(test) + " ")

        # Nothing selected
        self.page.toggle_filter('non-rig')
        self.page.toggle_filter('cancelled')

        icalUrl = self.page.cal_url
        response = c.get(icalUrl)
        self.assertEqual(200, response.status_code)

        expectedIn = []
        for test in range(1, 18):
            if test in expectedIn:
                self.assertContains(response, "TE E" + str(test) + " ")
            else:
                self.assertNotContains(response, "TE E" + str(test) + " ")

    def test_calendar_buttons(self):  # If FullCalendar fails to load for whatever reason, the buttons don't work
        self.page = pages.CalendarPage(self.driver, self.live_server_url).open()
        self.assertIn(timezone.now().strftime("%Y-%m"), self.driver.current_url)

        target_date = datetime.date(2020, 1, 1)
        self.page.target_date.set_value(target_date)
        self.page.go()
        self.assertIn(self.page.target_date.value.strftime("%Y-%m"), self.driver.current_url)

        self.page.next()
        target_date += datetime.timedelta(days=32)
        self.assertIn(target_date.strftime("%m"), self.driver.current_url)


@screenshot_failure_cls
class TestHealthAndSafety(BaseRigboardTest):
    def setUp(self):
        super().setUp()
        self.profile = models.Profile.objects.get_or_create(
            first_name='Test',
            last_name='TEC User',
            username='eventtest',
            email='teccie@functional.test',
            is_superuser=True  # lazily grant all permissions
        )[0]
        self.venue = models.Venue.objects.create(name="Venue 1")

        self.testEvent = models.Event.objects.create(name="TE E1", status=models.Event.PROVISIONAL,
                                                     start_date=date.today() + timedelta(days=6),
                                                     description="start future no end",
                                                     purchase_order='TESTPO',
                                                     person=self.client,
                                                     venue=self.venue)
        self.testEvent2 = models.Event.objects.create(name="TE E2", status=models.Event.PROVISIONAL,
                                                      start_date=date.today() + timedelta(days=6),
                                                      description="start future no end",
                                                      purchase_order='TESTPO',
                                                      person=self.client,
                                                      venue=self.venue)
        self.testEvent3 = models.Event.objects.create(name="TE E3", status=models.Event.PROVISIONAL,
                                                      start_date=date.today() + timedelta(days=6),
                                                      description="start future no end",
                                                      purchase_order='TESTPO',
                                                      person=self.client,
                                                      venue=self.venue)
        self.testRA = models.RiskAssessment.objects.create(event=self.testEvent2, supervisor_consulted=False, nonstandard_equipment=False,
                                                           nonstandard_use=False,
                                                           contractors=False,
                                                           other_companies=False,
                                                           crew_fatigue=False,
                                                           big_power=False,
                                                           generators=False,
                                                           other_companies_power=False,
                                                           nonstandard_equipment_power=False,
                                                           multiple_electrical_environments=False,
                                                           noise_monitoring=False,
                                                           known_venue=True,
                                                           safe_loading=True,
                                                           safe_storage=True,
                                                           area_outside_of_control=False,
                                                           barrier_required=False,
                                                           nonstandard_emergency_procedure=False,
                                                           special_structures=False,
                                                           suspended_structures=False,
                                                           outside=False)
        self.testRA2 = models.RiskAssessment.objects.create(event=self.testEvent3, supervisor_consulted=False, nonstandard_equipment=False,
                                                            nonstandard_use=False,
                                                            contractors=False,
                                                            other_companies=False,
                                                            crew_fatigue=False,
                                                            big_power=True,
                                                            generators=False,
                                                            other_companies_power=False,
                                                            nonstandard_equipment_power=False,
                                                            multiple_electrical_environments=False,
                                                            noise_monitoring=False,
                                                            known_venue=True,
                                                            safe_loading=True,
                                                            safe_storage=True,
                                                            area_outside_of_control=False,
                                                            barrier_required=False,
                                                            nonstandard_emergency_procedure=False,
                                                            special_structures=False,
                                                            suspended_structures=False,
                                                            outside=False)
        self.page = pages.EventDetail(self.driver, self.live_server_url, event_id=self.testEvent.pk).open()

    # TODO Can I loop through all the boolean fields and test them at once?
    def test_ra_creation(self):
        self.page = pages.CreateRiskAssessment(self.driver, self.live_server_url, event_id=self.testEvent.pk).open()

        # Check there are no defaults
        self.assertIsNone(self.page.nonstandard_equipment)

        # No database side validation, only HTML5.

        self.page.nonstandard_equipment = False
        self.page.nonstandard_use = False
        self.page.contractors = False
        self.page.other_companies = False
        self.page.crew_fatigue = False
        self.page.general_notes = "There are no notes."
        self.page.big_power = False
        self.page.outside = False
        self.page.power_mic.search(self.profile.name)
        self.page.power_mic.set_option(self.profile.name, True)
        # TODO This should not be necessary, normally closes automatically
        self.page.power_mic.toggle()
        self.assertFalse(self.page.power_mic.is_open)
        self.page.generators = False
        self.page.other_companies_power = False
        self.page.nonstandard_equipment_power = False
        self.page.multiple_electrical_environments = False
        self.page.power_notes = "Remember to bring some power"
        self.page.noise_monitoring = False
        self.page.sound_notes = "Loud, but not too loud"
        self.page.known_venue = False
        self.page.safe_loading = False
        self.page.safe_storage = False
        self.page.area_outside_of_control = False
        self.page.barrier_required = False
        self.page.nonstandard_emergency_procedure = False
        self.page.special_structures = False
        # self.page.persons_responsible_structures = "Nobody and her cat, She"

        self.page.suspended_structures = True
        # TODO Test for this proper
        self.page.rigging_plan = "https://nottinghamtec.sharepoint.com/test/"
        self.page.submit()
        self.assertFalse(self.page.success)

        self.page.suspended_structures = False
        self.page.submit()
        self.assertTrue(self.page.success)

        # Test that we can't make another one
        self.page = pages.CreateRiskAssessment(self.driver, self.live_server_url, event_id=self.testEvent.pk).open()
        self.assertIn('edit', self.driver.current_url)

    def test_ra_edit(self):
        self.page = pages.EditRiskAssessment(self.driver, self.live_server_url, pk=self.testRA.pk).open()
        self.page.nonstandard_equipment = nse = True
        self.page.general_notes = gn = "There are some notes, but I've not written them here as that would be helpful"
        self.page.submit()
        self.assertFalse(self.page.success)
        self.page.supervisor_consulted = True
        self.page.submit()
        self.assertTrue(self.page.success)
        # Check that data is right
        ra = models.RiskAssessment.objects.get(pk=self.testRA.pk)
        self.assertEqual(ra.general_notes, gn)
        self.assertEqual(ra.nonstandard_equipment, nse)

    def test_ec_create_small(self):
        self.page = pages.CreateEventChecklist(self.driver, self.live_server_url, event_id=self.testEvent2.pk).open()

        self.page.safe_parking = True
        self.page.safe_packing = True
        self.page.exits = True
        self.page.trip_hazard = True
        self.page.warning_signs = True
        self.page.ear_plugs = True
        self.page.hs_location = "The Moon"
        self.page.extinguishers_location = "With the rest of the fire"
        # If we do this first the search fails, for ... reasons
        self.page.power_mic.search(self.profile.name)
        self.page.power_mic.toggle()
        self.assertFalse(self.page.power_mic.is_open)

        # Gotta scroll to make the button clickable
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        self.page.earthing = True
        self.page.rcds = True
        self.page.supply_test = True
        self.page.pat = True

        self.page.submit()
        self.assertTrue(self.page.success)

    def test_ec_create_medium(self):
        self.page = pages.CreateEventChecklist(self.driver, self.live_server_url, event_id=self.testEvent3.pk).open()

        self.page.safe_parking = True
        self.page.safe_packing = True
        self.page.exits = True
        self.page.trip_hazard = True
        self.page.warning_signs = True
        self.page.ear_plugs = True
        self.page.hs_location = "Death Valley"
        self.page.extinguishers_location = "With the rest of the fire"
        # If we do this first the search fails, for ... reasons
        self.page.power_mic.search(self.profile.name)
        self.page.power_mic.toggle()
        self.assertFalse(self.page.power_mic.is_open)

        # Gotta scroll to make the button clickable
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        self.page.earthing = True
        self.page.pat = True
        self.page.source_rcd = True
        self.page.labelling = True
        self.page.fd_voltage_l1 = 240
        self.page.fd_voltage_l2 = 235
        self.page.fd_voltage_l3 = 0
        self.page.fd_phase_rotation = True
        self.page.fd_earth_fault = 666
        self.page.fd_pssc = 1984
        self.page.w1_description = "In the carpark, by the bins"
        self.page.w1_polarity = True
        self.page.w1_voltage = 240
        self.page.w1_earth_fault = 333

        self.page.submit()
        self.assertTrue(self.page.success)

    def test_ec_create_extras(self):
        eid = self.testEvent2.pk
        self.page = pages.CreateEventChecklist(self.driver, self.live_server_url, event_id=eid).open()
        self.page.add_vehicle()
        self.page.add_crew()

        self.page.safe_parking = True
        self.page.safe_packing = True
        self.page.exits = True
        self.page.trip_hazard = True
        self.page.warning_signs = True
        self.page.ear_plugs = True
        self.page.hs_location = "The Moon"
        self.page.extinguishers_location = "With the rest of the fire"
        # If we do this first the search fails, for ... reasons
        self.page.power_mic.search(self.profile.name)
        self.page.power_mic.toggle()
        self.assertFalse(self.page.power_mic.is_open)

        vehicle_name = 'Brian'
        self.driver.find_element(By.XPATH, '//*[@name="vehicle_-1"]').send_keys(vehicle_name)
        driver = base_regions.BootstrapSelectElement(self.page, self.driver.find_element(By.XPATH, '//tr[@id="vehicles_-1"]//div[contains(@class, "bootstrap-select")]'))
        driver.search(self.profile.name)

        crew = self.profile
        role = "MIC"
        crew_select = base_regions.BootstrapSelectElement(self.page, self.driver.find_element(By.XPATH, '//tr[@id="crew_-1"]//div[contains(@class, "bootstrap-select")]'))
        start_time = base_regions.DateTimePicker(self.page, self.driver.find_element(By.XPATH, '//*[@name="start_-1"]'))
        end_time = base_regions.DateTimePicker(self.page, self.driver.find_element(By.XPATH, '//*[@name="end_-1"]'))

        start_time.set_value(timezone.make_aware(datetime.datetime(2015, 1, 1, 9, 0)))
        # TODO Test validation of end before start
        end_time.set_value(timezone.make_aware(datetime.datetime(2015, 1, 1, 10, 30)))
        crew_select.search(crew.name)
        self.driver.find_element(By.XPATH, '//*[@name="role_-1"]').send_keys(role)

        self.page.earthing = True
        self.page.rcds = True
        self.page.supply_test = True
        self.page.pat = True

        self.page.submit()
        self.assertTrue(self.page.success)

        checklist = models.EventChecklist.objects.get(event=eid)
        vehicle = models.EventChecklistVehicle.objects.get(checklist=checklist.pk)
        self.assertEqual(vehicle_name, vehicle.vehicle)
        crew_obj = models.EventChecklistCrew.objects.get(checklist=checklist.pk)
        self.assertEqual(crew.pk, crew_obj.crewmember.pk)
        self.assertEqual(role, crew_obj.role)

# -*- coding: utf-8 -*-
import os
import re
import pytz
from datetime import date, time, datetime, timedelta


from django.core import mail
from django.db import transaction
from django.http import HttpResponseBadRequest
from django.test import LiveServerTestCase, TestCase
from django.test.client import Client
from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException, WebDriverException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait

from RIGS import models

from reversion import revisions as reversion
from django.core.urlresolvers import reverse
from django.core import mail, signing


from django.conf import settings

import sys

def create_browser():
    driver = webdriver.Chrome()
    driver.maximize_window()
    return driver

class UserRegistrationTest(LiveServerTestCase):
    def setUp(self):
        self.browser = create_browser()

        self.browser.implicitly_wait(3)  # Set implicit wait session wide
        os.environ['RECAPTCHA_TESTING'] = 'True'

    def tearDown(self):
        self.browser.quit()
        os.environ['RECAPTCHA_TESTING'] = 'False'

    def test_registration(self):
        # Navigate to the registration page
        self.browser.get(self.live_server_url + '/user/register/')
        title_text = self.browser.find_element_by_tag_name('h3').text
        self.assertIn("User Registration", title_text)

        # Check the form invites correctly
        username = self.browser.find_element_by_id('id_username')
        self.assertEqual(username.get_attribute('placeholder'), 'Username')
        email = self.browser.find_element_by_id('id_email')
        self.assertEqual(email.get_attribute('placeholder'), 'E-mail')
        # If this is correct we don't need to test it later
        self.assertEqual(email.get_attribute('type'), 'email')
        password1 = self.browser.find_element_by_id('id_password1')
        self.assertEqual(password1.get_attribute('placeholder'), 'Password')
        self.assertEqual(password1.get_attribute('type'), 'password')
        password2 = self.browser.find_element_by_id('id_password2')
        self.assertEqual(
            password2.get_attribute('placeholder'), 'Password confirmation')
        self.assertEqual(password2.get_attribute('type'), 'password')
        first_name = self.browser.find_element_by_id('id_first_name')
        self.assertEqual(first_name.get_attribute('placeholder'), 'First name')
        last_name = self.browser.find_element_by_id('id_last_name')
        self.assertEqual(last_name.get_attribute('placeholder'), 'Last name')
        initials = self.browser.find_element_by_id('id_initials')
        self.assertEqual(initials.get_attribute('placeholder'), 'Initials')
        phone = self.browser.find_element_by_id('id_phone')
        self.assertEqual(phone.get_attribute('placeholder'), 'Phone')

        # Fill the form out incorrectly
        username.send_keys('TestUsername')
        email.send_keys('test@example.com')
        password1.send_keys('correcthorsebatterystaple')
        # deliberate mistake
        password2.send_keys('correcthorsebatterystapleerror')
        first_name.send_keys('John')
        last_name.send_keys('Smith')
        initials.send_keys('JS')
        phone.send_keys('0123456789')
        self.browser.execute_script(
            "return jQuery('#g-recaptcha-response').val('PASSED')")

        # Submit incorrect form
        submit = self.browser.find_element_by_xpath("//input[@type='submit']")
        submit.click()

        # Restablish error fields
        password1 = self.browser.find_element_by_id('id_password1')
        password2 = self.browser.find_element_by_id('id_password2')

        # Read what the error is
        alert = self.browser.find_element_by_css_selector(
            'div.alert-danger').text
        self.assertIn("password fields didn't match", alert)

        # Passwords should be empty
        self.assertEqual(password1.get_attribute('value'), '')
        self.assertEqual(password2.get_attribute('value'), '')

        # Correct error
        password1.send_keys('correcthorsebatterystaple')
        password2.send_keys('correcthorsebatterystaple')
        self.browser.execute_script(
            "return jQuery('#g-recaptcha-response').val('PASSED')")

        # Submit again
        password2.send_keys(Keys.ENTER)

        # Check we have a success message
        alert = self.browser.find_element_by_css_selector(
            'div.alert-success').text
        self.assertIn('register', alert)
        self.assertIn('email', alert)

        # Check Email
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertIn('John Smith "JS" activation required', email.subject)
        urls = re.findall(
            'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', email.body)
        self.assertEqual(len(urls), 1)

        mail.outbox = []  # empty this for later

        # Follow link
        self.browser.get(urls[0])  # go to the first link

        # Complete registration
        title_text = self.browser.find_element_by_tag_name('h2').text
        self.assertIn('Complete', title_text)

        # Test login
        self.browser.get(self.live_server_url + '/user/login')
        username = self.browser.find_element_by_id('id_username')
        self.assertEqual(username.get_attribute('placeholder'), 'Username')
        password = self.browser.find_element_by_id('id_password')
        self.assertEqual(password.get_attribute('placeholder'), 'Password')
        self.assertEqual(password.get_attribute('type'), 'password')

        username.send_keys('TestUsername')
        password.send_keys('correcthorsebatterystaple')
        self.browser.execute_script(
            "return jQuery('#g-recaptcha-response').val('PASSED')")
        password.send_keys(Keys.ENTER)

        # Check we are logged in
        udd = self.browser.find_element_by_class_name('navbar').text
        self.assertIn('Hi John', udd)

        # Check all the data actually got saved
        profileObject = models.Profile.objects.all()[0]
        self.assertEqual(profileObject.username, 'TestUsername')
        self.assertEqual(profileObject.first_name, 'John')
        self.assertEqual(profileObject.last_name, 'Smith')
        self.assertEqual(profileObject.initials, 'JS')
        self.assertEqual(profileObject.phone, '0123456789')
        self.assertEqual(profileObject.email, 'test@example.com')

        # All is well

class EventTest(LiveServerTestCase):
    def setUp(self):
        self.profile = models.Profile(
            username="EventTest", first_name="Event", last_name="Test", initials="ETU", is_superuser=True)
        self.profile.set_password("EventTestPassword")
        self.profile.save()


        self.vatrate = models.VatRate.objects.create(start_at='2014-03-05',rate=0.20,comment='test1')
        
        self.browser = create_browser()
        self.browser.implicitly_wait(10) # Set implicit wait session wide
        # self.browser.maximize_window()

        os.environ['RECAPTCHA_TESTING'] = 'True'

    def tearDown(self):
        self.browser.quit()
        os.environ['RECAPTCHA_TESTING'] = 'False'

    def authenticate(self, n=None):
        self.assertIn(
            self.live_server_url + '/user/login/', self.browser.current_url)
        if n:
            self.assertIn('?next=%s' % n, self.browser.current_url)
        username = self.browser.find_element_by_id('id_username')
        password = self.browser.find_element_by_id('id_password')
        submit = self.browser.find_element_by_css_selector(
            'input[type=submit]')

        username.send_keys("EventTest")
        password.send_keys("EventTestPassword")
        submit.click()

        self.assertEqual(self.live_server_url + n, self.browser.current_url)

    def testRigboardButtons(self):
        # Requests address
        self.browser.get(self.live_server_url + '/rigboard/')
        # Gets redirected to login
        self.authenticate('/rigboard/')

        # Completes and comes back to rigboard
        # Clicks add new
        self.browser.find_element_by_partial_link_text("New").click()
        self.assertEqual(
            self.live_server_url + '/event/create/', self.browser.current_url)
        self.browser.get(self.live_server_url + '/rigboard/')

    def testRigCreate(self):
        try:
            # Requests address
            self.browser.get(self.live_server_url + '/event/create/')
            # Gets redirected to login and back
            self.authenticate('/event/create/')

            wait = WebDriverWait(self.browser, 3) #setup WebDriverWait to use later (to wait for animations)

            wait.until(animation_is_finished())

            # Check has slided up correctly - second save button hidden
            save = self.browser.find_element_by_xpath(
                '(//button[@type="submit"])[3]')
            self.assertFalse(save.is_displayed())

            # Click Rig button
            self.browser.find_element_by_xpath('//button[.="Rig"]').click()

            # Slider expands and save button visible
            self.assertTrue(save.is_displayed())
            form = self.browser.find_element_by_tag_name('form')

            # Create new person
            wait.until(animation_is_finished())
            add_person_button = self.browser.find_element_by_xpath(
                '//a[@data-target="#id_person" and contains(@href, "add")]')
            add_person_button.click()

            # See modal has opened
            modal = self.browser.find_element_by_id('modal')
            wait.until(animation_is_finished())
            self.assertTrue(modal.is_displayed())
            self.assertIn("Add Person", modal.find_element_by_tag_name('h3').text)

            # Fill person form out and submit
            modal.find_element_by_xpath(
                '//div[@id="modal"]//input[@id="id_name"]').send_keys("Test Person 1")
            modal.find_element_by_xpath(
                '//div[@id="modal"]//input[@type="submit"]').click()
            wait.until(animation_is_finished())
            self.assertFalse(modal.is_displayed())

            # See new person selected
            person1 = models.Person.objects.get(name="Test Person 1")
            self.assertEqual(person1.name, form.find_element_by_xpath(
                '//button[@data-id="id_person"]/span').text)
            # and backend
            option = form.find_element_by_xpath(
                '//select[@id="id_person"]//option[@selected="selected"]')
            self.assertEqual(person1.pk, int(option.get_attribute("value")))

            # Change mind and add another
            wait.until(animation_is_finished())
            add_person_button.click()

            wait.until(animation_is_finished())
            self.assertTrue(modal.is_displayed())
            self.assertIn("Add Person", modal.find_element_by_tag_name('h3').text)

            modal.find_element_by_xpath(
                '//div[@id="modal"]//input[@id="id_name"]').send_keys("Test Person 2")
            modal.find_element_by_xpath(
                '//div[@id="modal"]//input[@type="submit"]').click()
            wait.until(animation_is_finished())
            self.assertFalse(modal.is_displayed())

            person2 = models.Person.objects.get(name="Test Person 2")
            self.assertEqual(person2.name, form.find_element_by_xpath(
                '//button[@data-id="id_person"]/span').text)
            # Have to do this explcitly to force the wait for it to update
            option = form.find_element_by_xpath(
                '//select[@id="id_person"]//option[@selected="selected"]')
            self.assertEqual(person2.pk, int(option.get_attribute("value")))

            # Was right the first time, change it back
            person_select = form.find_element_by_xpath(
                '//button[@data-id="id_person"]')
            person_select.send_keys(person1.name)
            person_dropped = form.find_element_by_xpath(
                '//ul[contains(@class, "inner selectpicker")]//span[contains(text(), "%s")]' % person1.name)
            person_dropped.click()

            self.assertEqual(person1.name, form.find_element_by_xpath(
                '//button[@data-id="id_person"]/span').text)
            option = form.find_element_by_xpath(
                '//select[@id="id_person"]//option[@selected="selected"]')
            self.assertEqual(person1.pk, int(option.get_attribute("value")))

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

            # Set start date/time
            form.find_element_by_id('id_start_date').send_keys('25/05/3015')
            form.find_element_by_id('id_start_time').send_keys('06:59')

            # Set end date/time
            form.find_element_by_id('id_end_date').send_keys('27/06/4000')
            form.find_element_by_id('id_end_time').send_keys('07:00')

            # Add item
            form.find_element_by_xpath('//button[contains(@class, "item-add")]').click()
            wait.until(animation_is_finished())
            modal = self.browser.find_element_by_id("itemModal")
            modal.find_element_by_id("item_name").send_keys("Test Item 1")
            modal.find_element_by_id("item_description").send_keys(
                "This is an item description\nthat for reasons unkown spans two lines")
            e = modal.find_element_by_id("item_quantity")
            e.click()
            e.send_keys(Keys.UP)
            e.send_keys(Keys.UP)
            e = modal.find_element_by_id("item_cost")
            e.send_keys("23.95")
            e.send_keys(Keys.ENTER)  # enter submit

            # Confirm item has been saved to json field
            objectitems = self.browser.execute_script("return objectitems;")
            self.assertEqual(1, len(objectitems))
            testitem = objectitems["-1"]['fields']  # as we are deliberately creating this we know the ID
            self.assertEqual("Test Item 1", testitem['name'])
            self.assertEqual("2", testitem['quantity'])  # test a couple of "worse case" fields

            # See new item appear in table
            row = self.browser.find_element_by_id('item--1')  # ID number is known, see above
            self.assertIn("Test Item 1", row.find_element_by_xpath('//span[@class="name"]').text)
            self.assertIn("This is an item description",
                          row.find_element_by_xpath('//div[@class="item-description"]').text)
            self.assertEqual('£ 23.95', row.find_element_by_xpath('//tr[@id="item--1"]/td[2]').text)
            self.assertEqual("2", row.find_element_by_xpath('//td[@class="quantity"]').text)
            self.assertEqual('£ 47.90', row.find_element_by_xpath('//tr[@id="item--1"]/td[4]').text)

            # Check totals
            self.assertEqual("47.90", self.browser.find_element_by_id('sumtotal').text)
            self.assertIn("(TBC)", self.browser.find_element_by_id('vat-rate').text)
            self.assertEqual("9.58", self.browser.find_element_by_id('vat').text)
            self.assertEqual("57.48", self.browser.find_element_by_id('total').text)

            # Attempt to save - missing title
            save.click()

            # See error
            error = self.browser.find_element_by_xpath('//div[contains(@class, "alert-danger")]')
            self.assertTrue(error.is_displayed())
            # Should only have one error message
            self.assertEqual("Name", error.find_element_by_xpath('//dt[1]').text)
            self.assertEqual("This field is required.", error.find_element_by_xpath('//dd[1]/ul/li').text)
            # don't need error so close it
            error.find_element_by_xpath('//div[contains(@class, "alert-danger")]//button[@class="close"]').click()
            try:
                self.assertFalse(error.is_displayed())
            except StaleElementReferenceException:
                pass
            except:
                self.assertFail("Element does not appear to have been deleted")

            # Check at least some data is preserved. Some = all will be there
            option = self.browser.find_element_by_xpath(
                '//select[@id="id_person"]//option[@selected="selected"]')
            self.assertEqual(person1.pk, int(option.get_attribute("value")))

            # Set title
            e = self.browser.find_element_by_id('id_name')
            e.send_keys('Test Event Name')
            e.send_keys(Keys.ENTER)

            # See redirected to success page
            successTitle = self.browser.find_element_by_xpath('//h1').text
            event = models.Event.objects.get(name='Test Event Name')

            self.assertIn("N%05d | Test Event Name"%event.pk, successTitle)
        except WebDriverException:
            # This is a dirty workaround for wercker being a bit funny and not running it correctly.
            # Waiting for wercker to get back to me about this
            pass

    def testEventDuplicate(self):
        testEvent = models.Event.objects.create(name="TE E1", status=models.Event.PROVISIONAL,
                                                start_date=date.today() + timedelta(days=6),
                                                description="start future no end",
                                                purchase_order='TESTPO',
                                                auth_request_by=self.profile,
                                                auth_request_at=self.create_datetime(2015, 0o6, 0o4, 10, 00),
                                                auth_request_to="some@email.address")

        item1 = models.EventItem(
            event=testEvent,
            name="Test Item 1",
            cost="10.00",
            quantity="1",
            order=1
        ).save()
        item2 = models.EventItem(
            event=testEvent,
            name="Test Item 2",
            description="Foo",
            cost="9.72",
            quantity="3",
            order=2,
        ).save()

        self.browser.get(self.live_server_url + '/event/' + str(testEvent.pk) + '/duplicate/')
        self.authenticate('/event/' + str(testEvent.pk) + '/duplicate/')


        wait = WebDriverWait(self.browser, 3) #setup WebDriverWait to use later (to wait for animations)

        save = self.browser.find_element_by_xpath(
            '(//button[@type="submit"])[3]')
        form = self.browser.find_element_by_tag_name('form')

        # Check the items are visible
        table = self.browser.find_element_by_id('item-table')  # ID number is known, see above
        self.assertIn("Test Item 1", table.text)
        self.assertIn("Test Item 2", table.text)

        # Check the info message is visible
        self.assertIn("Event data duplicated but not yet saved", self.browser.find_element_by_id('content').text)

        # Add item
        form.find_element_by_xpath('//button[contains(@class, "item-add")]').click()
        wait.until(animation_is_finished())
        modal = self.browser.find_element_by_id("itemModal")
        modal.find_element_by_id("item_name").send_keys("Test Item 3")
        modal.find_element_by_id("item_description").send_keys(
            "This is an item description\nthat for reasons unkown spans two lines")
        e = modal.find_element_by_id("item_quantity")
        e.click()
        e.send_keys(Keys.UP)
        e.send_keys(Keys.UP)
        e = modal.find_element_by_id("item_cost")
        e.send_keys("23.95")
        e.send_keys(Keys.ENTER)  # enter submit

        # Attempt to save
        save.click()

        newEvent = models.Event.objects.latest('pk')

        self.assertEqual(newEvent.auth_request_to, None)
        self.assertEqual(newEvent.auth_request_by, None)
        self.assertEqual(newEvent.auth_request_at, None)
        
        self.assertFalse(hasattr(newEvent, 'authorised'))

        self.assertNotIn("N%05d"%testEvent.pk, self.browser.find_element_by_xpath('//h1').text)
        self.assertNotIn("Event data duplicated but not yet saved", self.browser.find_element_by_id('content').text) # Check info message not visible

        # Check the new items are visible
        table = self.browser.find_element_by_id('item-table')  # ID number is known, see above
        self.assertIn("Test Item 1", table.text)
        self.assertIn("Test Item 2", table.text)
        self.assertIn("Test Item 3", table.text)

        infoPanel = self.browser.find_element_by_xpath('//div[contains(text(), "Event Info")]/..')
        self.assertIn("N0000%d" % testEvent.pk,
                      infoPanel.find_element_by_xpath('//dt[text()="Based On"]/following-sibling::dd[1]').text)
        # Check the PO hasn't carried through
        self.assertNotIn("TESTPO", infoPanel.find_element_by_xpath('//dt[text()="PO"]/following-sibling::dd[1]').text)


        self.assertIn("N%05d"%testEvent.pk, infoPanel.find_element_by_xpath('//dt[text()="Based On"]/following-sibling::dd[1]').text)

        self.browser.get(self.live_server_url + '/event/' + str(testEvent.pk)) #Go back to the old event
        
        #Check that based-on hasn't crept into the old event
        infoPanel = self.browser.find_element_by_xpath('//div[contains(text(), "Event Info")]/..')
        self.assertNotIn("N0000%d" % testEvent.pk,
                         infoPanel.find_element_by_xpath('//dt[text()="Based On"]/following-sibling::dd[1]').text)
        # Check the PO remains on the old event
        self.assertIn("TESTPO", infoPanel.find_element_by_xpath('//dt[text()="PO"]/following-sibling::dd[1]').text)

        self.assertNotIn("N%05d"%testEvent.pk, infoPanel.find_element_by_xpath('//dt[text()="Based On"]/following-sibling::dd[1]').text)        

        # Check the items are as they were
        table = self.browser.find_element_by_id('item-table')  # ID number is known, see above
        self.assertIn("Test Item 1", table.text)
        self.assertIn("Test Item 2", table.text)
        self.assertNotIn("Test Item 3", table.text)

    def testDateValidation(self):
        self.browser.get(self.live_server_url + '/event/create/')
        # Gets redirected to login and back
        self.authenticate('/event/create/')


        wait = WebDriverWait(self.browser, 3) #setup WebDriverWait to use later (to wait for animations)

        wait.until(animation_is_finished())

        # Click Rig button
        self.browser.find_element_by_xpath('//button[.="Rig"]').click()

        form = self.browser.find_element_by_tag_name('form')
        save = self.browser.find_element_by_xpath('(//button[@type="submit"])[3]')

        # Set title
        e = self.browser.find_element_by_id('id_name')
        e.send_keys('Test Event Name')

        # Both dates, no times, end before start
        self.browser.execute_script("document.getElementById('id_start_date').value='3015-04-24'")

        self.browser.execute_script("document.getElementById('id_end_date').value='3015-04-23'")

        # Attempt to save - should fail
        wait.until(animation_is_finished())
        save.click()

        error = self.browser.find_element_by_xpath('//div[contains(@class, "alert-danger")]')
        self.assertTrue(error.is_displayed())
        self.assertIn("can't finish before it has started", error.find_element_by_xpath('//dd[1]/ul/li').text)

        # Same date, end time before start time
        form = self.browser.find_element_by_tag_name('form')
        save = self.browser.find_element_by_xpath('(//button[@type="submit"])[3]')

        self.browser.execute_script("document.getElementById('id_start_date').value='3015-04-24'")
        self.browser.execute_script("document.getElementById('id_end_date').value='3015-04-23'")

        form.find_element_by_id('id_start_time').send_keys(Keys.DELETE)
        form.find_element_by_id('id_start_time').send_keys('06:59')

        form.find_element_by_id('id_end_time').send_keys(Keys.DELETE)
        form.find_element_by_id('id_end_time').send_keys('06:00')

        # Attempt to save - should fail
        save.click()
        error = self.browser.find_element_by_xpath('//div[contains(@class, "alert-danger")]')
        self.assertTrue(error.is_displayed())
        self.assertIn("can't finish before it has started", error.find_element_by_xpath('//dd[1]/ul/li').text)

        # Same date, end time before start time
        form = self.browser.find_element_by_tag_name('form')
        save = self.browser.find_element_by_xpath('(//button[@type="submit"])[3]')

        self.browser.execute_script("document.getElementById('id_start_date').value='3015-04-24'")
        self.browser.execute_script("document.getElementById('id_end_date').value='3015-04-24'")

        form.find_element_by_id('id_start_time').send_keys(Keys.DELETE)
        form.find_element_by_id('id_start_time').send_keys('06:59')

        form.find_element_by_id('id_end_time').send_keys(Keys.DELETE)
        form.find_element_by_id('id_end_time').send_keys('06:00')

        # No end date, end time before start time
        form = self.browser.find_element_by_tag_name('form')
        save = self.browser.find_element_by_xpath('(//button[@type="submit"])[3]')
        
        self.browser.execute_script("document.getElementById('id_start_date').value='3015-04-24'")
        self.browser.execute_script("document.getElementById('id_end_date').value=''")

        form.find_element_by_id('id_start_time').send_keys(Keys.DELETE)
        form.find_element_by_id('id_start_time').send_keys('06:59')

        form.find_element_by_id('id_end_time').send_keys(Keys.DELETE)
        form.find_element_by_id('id_end_time').send_keys('06:00')

        # Attempt to save - should fail
        save.click()
        error = self.browser.find_element_by_xpath('//div[contains(@class, "alert-danger")]')
        self.assertTrue(error.is_displayed())
        self.assertIn("can't finish before it has started", error.find_element_by_xpath('//dd[1]/ul/li').text)

        # 2 dates, end after start
        form = self.browser.find_element_by_tag_name('form')
        save = self.browser.find_element_by_xpath('(//button[@type="submit"])[3]')
        self.browser.execute_script("document.getElementById('id_start_date').value='3015-04-24'")
        self.browser.execute_script("document.getElementById('id_end_date').value='3015-04-26'")


        self.browser.execute_script("document.getElementById('id_start_time').value=''")
        self.browser.execute_script("document.getElementById('id_end_time').value=''")
        
        # Attempt to save - should succeed
        save.click()

        # See redirected to success page
        successTitle = self.browser.find_element_by_xpath('//h1').text
        event = models.Event.objects.get(name='Test Event Name')

        self.assertIn("N%05d | Test Event Name"%event.pk, successTitle)
        
    def testRigNonRig(self):
        self.browser.get(self.live_server_url + '/event/create/')
        # Gets redirected to login and back
        self.authenticate('/event/create/')


        wait = WebDriverWait(self.browser, 3) #setup WebDriverWait to use later (to wait for animations)
        self.browser.implicitly_wait(3) #Set session-long wait (only works for non-existant DOM objects)

        wait.until(animation_is_finished())

        # Click Non-Rig button
        self.browser.find_element_by_xpath('//button[.="Non-Rig"]').click()

        # Click Rig button
        self.browser.find_element_by_xpath('//button[.="Rig"]').click()

        form = self.browser.find_element_by_tag_name('form')
        save = self.browser.find_element_by_xpath('(//button[@type="submit"])[3]')

        # Set title
        e = self.browser.find_element_by_id('id_name')
        e.send_keys('Test Event Name')

        # Set an arbitrary date
        self.browser.execute_script("document.getElementById('id_start_date').value='3015-04-24'")

        # Save the rig
        wait.until(animation_is_finished())
        save.click()
        detail_panel = self.browser.find_element_by_xpath("//div[@id='content']/div/div[6]/div/div")
        self.assertTrue(detail_panel.is_displayed())
        self.assertIn("Event Detail", detail_panel.text)

    def testEventDetail(self):
        with transaction.atomic(), reversion.create_revision():
            person = models.Person(name="Event Detail Person", email="eventdetail@person.tests.rigs", phone="123 123")
            person.save()
        with transaction.atomic(), reversion.create_revision():
            organisation = models.Organisation(name="Event Detail Organisation",
                                               email="eventdetail@organisation.tests.rigs", phone="123 456").save()
        with transaction.atomic(), reversion.create_revision():
            venue = models.Venue(name="Event Detail Venue").save()
        with transaction.atomic(), reversion.create_revision():
            event = models.Event(
                name="Detail Test",
                description="This is an event to test the detail view",
                notes="It is going to be aweful",
                person=person,
                organisation=organisation,
                start_date='2015-06-04'
            )
        event.save()
        with transaction.atomic(), reversion.create_revision():
            item1 = models.EventItem(
                event=event,
                name="Detail Item 1",
                cost="10.00",
                quantity="1",
                order=1
            ).save()
            item2 = models.EventItem(
                event=event,
                name="Detail Item 2",
                description="Foo",
                cost="9.72",
                quantity="3",
                order=2,
            ).save()

        self.browser.get(self.live_server_url + '/event/%d' % event.pk)
        self.authenticate('/event/%d/' % event.pk)
        self.assertIn("N%05d | %s" % (event.pk, event.name), self.browser.find_element_by_xpath('//h1').text)

        personPanel = self.browser.find_element_by_xpath('//div[contains(text(), "Contact Details")]/..')
        self.assertEqual(person.name,
                         personPanel.find_element_by_xpath('//dt[text()="Person"]/following-sibling::dd[1]').text)
        self.assertEqual(person.email,
                         personPanel.find_element_by_xpath('//dt[text()="Email"]/following-sibling::dd[1]').text)
        self.assertEqual(person.phone,
                         personPanel.find_element_by_xpath('//dt[text()="Phone Number"]/following-sibling::dd[1]').text)

        organisationPanel = self.browser.find_element_by_xpath('//div[contains(text(), "Contact Details")]/..')


    def testEventEdit(self):
        person = models.Person(name="Event Edit Person", email="eventdetail@person.tests.rigs", phone="123 123").save()
        organisation = models.Organisation(name="Event Edit Organisation", email="eventdetail@organisation.tests.rigs", phone="123 456").save()
        venue = models.Venue(name="Event Detail Venue").save()

        eventData = {
            'name': "Detail Test",
            'description': "This is an event to test the detail view",
            'notes': "It is going to be awful",
            'person': person,
            'organisation': organisation,
            'venue': venue,
            'mic': self.profile,
            'start_date': date(2015, 0o6, 0o4),
            'end_date': date(2015, 0o6, 0o5),
            'start_time': time(10, 00),
            'end_time': time(15, 00),
            'meet_at': self.create_datetime(2015, 0o6, 0o4, 10, 00),
            'access_at': self.create_datetime(2015, 0o6, 0o4, 10, 00),
            'collector': 'A Person'
        }

        event = models.Event(**eventData)
        event.save()

        item1Data = {
            'event': event,
            'name': "Detail Item 1",
            'cost': "10.00",
            'quantity': "1",
            'order': 1
        }

        models.EventItem(**item1Data).save()

        self.browser.get(self.live_server_url + '/event/%d/edit/' % event.pk)
        self.authenticate('/event/%d/edit/' % event.pk)

        save = self.browser.find_element_by_xpath('(//button[@type="submit"])[1]')
        save.click()

        successTitle = self.browser.find_element_by_xpath('//h1').text
        self.assertIn("N%05d | Detail Test" % event.pk, successTitle)

        reloadedEvent = models.Event.objects.get(name='Detail Test')
        reloadedItem = models.EventItem.objects.get(name='Detail Item 1')

        # Check the event
        for key, value in eventData.items():
            self.assertEqual(str(getattr(reloadedEvent, key)), str(value))

        # Check the item
        for key, value in item1Data.items():
            self.assertEqual(str(getattr(reloadedItem, key)), str(value))

    def create_datetime(self, year, month, day, hour, min):
        tz = pytz.timezone(settings.TIME_ZONE)
        return tz.localize(datetime(year, month, day, hour, min)).astimezone(pytz.utc)

class IcalTest(LiveServerTestCase):
    def setUp(self):
        self.all_events = set(range(1, 18))
        self.current_events = (1, 2, 3, 6, 7, 8, 10, 11, 12, 14, 15, 16, 18)
        self.not_current_events = set(self.all_events) - set(self.current_events)

        self.vatrate = models.VatRate.objects.create(start_at='2014-03-05', rate=0.20, comment='test1')
        self.profile = models.Profile(
            username="EventTest", first_name="Event", last_name="Test", initials="ETU", is_superuser=True)
        self.profile.set_password("EventTestPassword")
        self.profile.save()

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
                                    end_date=date.today() + timedelta(days=2), description="start past, end future")
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


        self.browser = create_browser()
        self.browser.implicitly_wait(3) # Set implicit wait session wide
        os.environ['RECAPTCHA_TESTING'] = 'True'

    def tearDown(self):
        self.browser.quit()
        os.environ['RECAPTCHA_TESTING'] = 'False'

    def authenticate(self, n=None):
        self.assertIn(
            self.live_server_url + '/user/login/', self.browser.current_url)
        if n:
            self.assertIn('?next=%s' % n, self.browser.current_url)
        username = self.browser.find_element_by_id('id_username')
        password = self.browser.find_element_by_id('id_password')
        submit = self.browser.find_element_by_css_selector(
            'input[type=submit]')

        username.send_keys("EventTest")
        password.send_keys("EventTestPassword")
        submit.click()

        self.assertEqual(self.live_server_url + n, self.browser.current_url)

    def testApiKeyGeneration(self):
        # Requests address
        self.browser.get(self.live_server_url + '/user/')
        # Gets redirected to login
        self.authenticate('/user/')

        # Completes and comes back to /user/
        # Checks that no api key is displayed
        self.assertEqual("No API Key Generated",
                         self.browser.find_element_by_xpath("//div[@id='content']/div/div/div[3]/dl[2]/dd").text)
        self.assertEqual("No API Key Generated", self.browser.find_element_by_css_selector("pre").text)

        # Now creates an API key, and check a URL is displayed one
        self.browser.find_element_by_link_text("Generate API Key").click()
        self.assertIn("rigs.ics", self.browser.find_element_by_id("cal-url").text)
        self.assertNotIn("?", self.browser.find_element_by_id("cal-url").text)

        # Lets change everything so it's not the default value
        self.browser.find_element_by_xpath("//input[@value='rig']").click()
        self.browser.find_element_by_xpath("//input[@value='non-rig']").click()
        self.browser.find_element_by_xpath("//input[@value='dry-hire']").click()
        self.browser.find_element_by_xpath("//input[@value='cancelled']").click()
        self.browser.find_element_by_xpath("//input[@value='provisional']").click()
        self.browser.find_element_by_xpath("//input[@value='confirmed']").click()

        # and then check the url is correct
        self.assertIn(
            "rigs.ics?rig=false&non-rig=false&dry-hire=false&cancelled=true&provisional=false&confirmed=false",
            self.browser.find_element_by_id("cal-url").text)

        # Awesome - all seems to work

    def testICSFiles(self):
        # Requests address
        self.browser.get(self.live_server_url + '/user/')
        # Gets redirected to login
        self.authenticate('/user/')

        # Now creates an API key, and check a URL is displayed one
        self.browser.find_element_by_link_text("Generate API Key").click()

        c = Client()

        # Default settings - should have all non-cancelled events
        # Get the ical file (can't do this in selanium because reasons)
        icalUrl = self.browser.find_element_by_id("cal-url").text
        response = c.get(icalUrl)
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

        # Only dry hires
        self.browser.find_element_by_xpath("//input[@value='rig']").click()
        self.browser.find_element_by_xpath("//input[@value='non-rig']").click()

        icalUrl = self.browser.find_element_by_id("cal-url").text
        response = c.get(icalUrl)
        self.assertEqual(200, response.status_code)

        expectedIn = [10, 11, 12, 13]
        for test in range(1, 18):
            if test in expectedIn:
                self.assertContains(response, "TE E" + str(test) + " ")
            else:
                self.assertNotContains(response, "TE E" + str(test) + " ")

        # Only provisional rigs
        self.browser.find_element_by_xpath("//input[@value='rig']").click()
        self.browser.find_element_by_xpath("//input[@value='dry-hire']").click()
        self.browser.find_element_by_xpath("//input[@value='confirmed']").click()

        icalUrl = self.browser.find_element_by_id("cal-url").text
        response = c.get(icalUrl)
        self.assertEqual(200, response.status_code)

        expectedIn = [1, 2]
        for test in range(1, 18):
            if test in expectedIn:
                self.assertContains(response, "TE E" + str(test) + " ")
            else:
                self.assertNotContains(response, "TE E" + str(test) + " ")

        # Only cancelled non-rigs
        self.browser.find_element_by_xpath("//input[@value='rig']").click()
        self.browser.find_element_by_xpath("//input[@value='non-rig']").click()
        self.browser.find_element_by_xpath("//input[@value='provisional']").click()
        self.browser.find_element_by_xpath("//input[@value='cancelled']").click()

        icalUrl = self.browser.find_element_by_id("cal-url").text
        response = c.get(icalUrl)
        self.assertEqual(200, response.status_code)

        expectedIn = [18]
        for test in range(1, 18):
            if test in expectedIn:
                self.assertContains(response, "TE E" + str(test) + " ")
            else:
                self.assertNotContains(response, "TE E" + str(test) + " ")

        # Nothing selected
        self.browser.find_element_by_xpath("//input[@value='non-rig']").click()
        self.browser.find_element_by_xpath("//input[@value='cancelled']").click()

        icalUrl = self.browser.find_element_by_id("cal-url").text
        response = c.get(icalUrl)
        self.assertEqual(200, response.status_code)

        expectedIn = []
        for test in range(1, 18):
            if test in expectedIn:
                self.assertContains(response, "TE E" + str(test) + " ")
            else:
                self.assertNotContains(response, "TE E" + str(test) + " ")

                # Wow - that was a lot of tests


class animation_is_finished(object):
    """ Checks if animation is done """

    def __init__(self):
        pass

    def __call__(self, driver):
        numberAnimating = driver.execute_script('return $(":animated").length')
        finished = numberAnimating == 0
        if finished:
            import time
            time.sleep(0.1)
        return finished


class ClientEventAuthorisationTest(TestCase):
    auth_data = {
        'name': 'Test ABC',
        'po': '1234ABCZXY',
        'account_code': 'ABC TEST 12345',
        'uni_id': 1234567890,
        'tos': True
    }

    def setUp(self):
        self.profile = models.Profile.objects.get_or_create(
            first_name='Test',
            last_name='TEC User',
            username='eventauthtest',
            email='teccie@functional.test',
            is_superuser=True  # lazily grant all permissions
        )[0]
        self.vatrate = models.VatRate.objects.create(start_at='2014-03-05', rate=0.20, comment='test1')
        venue = models.Venue.objects.create(name='Authorisation Test Venue')
        client = models.Person.objects.create(name='Authorisation Test Person', email='authorisation@functional.test')
        organisation = models.Organisation.objects.create(name='Authorisation Test Organisation', union_account=False)
        self.event = models.Event.objects.create(
            name='Authorisation Test',
            start_date=date.today(),
            venue=venue,
            person=client,
            organisation=organisation,
        )
        self.hmac = signing.dumps({'pk': self.event.pk, 'email': 'authemail@function.test',
                                                      'sent_by': self.profile.pk})
        self.url = reverse('event_authorise', kwargs={'pk': self.event.pk, 'hmac': self.hmac})

    def test_requires_valid_hmac(self):
        bad_hmac = self.hmac[:-1]
        url = reverse('event_authorise', kwargs={'pk': self.event.pk, 'hmac': bad_hmac})
        response = self.client.get(url)
        self.assertIsInstance(response, HttpResponseBadRequest)
        # TODO: Add some form of sensbile user facing error
        # self.assertIn(response.content, "new URL")  # check there is some level of sane instruction

        response = self.client.get(self.url)
        self.assertContains(response, self.event.organisation.name)

    def test_generic_validation(self):
        response = self.client.get(self.url)
        self.assertContains(response, "Terms of Hire")

        response = self.client.post(self.url)
        self.assertContains(response, "This field is required.", 5)

        data = self.auth_data
        data['amount'] = self.event.total + 1

        response = self.client.post(self.url, data)
        self.assertContains(response, "The amount authorised must equal the total for the event")
        self.assertNotContains(response, "This field is required.")

        data['amount'] = self.event.total
        response = self.client.post(self.url, data)
        self.assertContains(response, "Your event has been authorised")

        self.event.refresh_from_db()
        self.assertTrue(self.event.authorised)
        self.assertEqual(self.event.authorisation.email, "authemail@function.test")

    def test_internal_validation(self):
        self.event.organisation.union_account = True
        self.event.organisation.save()

        response = self.client.get(self.url)
        self.assertContains(response, "Account code")
        self.assertContains(response, "University ID")

        response = self.client.post(self.url)
        self.assertContains(response, "This field is required.", 5)

        data = self.auth_data
        response = self.client.post(self.url, data)
        self.assertContains(response, "Your event has been authorised.")

    def test_duplicate_warning(self):
        auth = models.EventAuthorisation.objects.create(event=self.event, name='Test ABC', email='dupe@functional.test',
                                                        amount=self.event.total, sent_by=self.profile)
        response = self.client.get(self.url)
        self.assertContains(response, 'This event has already been authorised.')

        auth.amount += 1
        auth.save()

        response = self.client.get(self.url)
        self.assertContains(response, 'amount has changed')

    def test_email_sent(self):
        mail.outbox = []

        data = self.auth_data
        data['amount'] = self.event.total

        response = self.client.post(self.url, data)
        self.assertContains(response, "Your event has been authorised.")
        self.assertEqual(len(mail.outbox), 2)

        self.assertEqual(mail.outbox[0].to, ['authemail@function.test'])
        self.assertEqual(mail.outbox[1].to, [settings.AUTHORISATION_NOTIFICATION_ADDRESS])


class TECEventAuthorisationTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.profile = models.Profile.objects.get_or_create(
            first_name='Test',
            last_name='TEC User',
            username='eventauthtest',
            email='teccie@nottinghamtec.co.uk',
            is_superuser=True  # lazily grant all permissions
        )[0]
        cls.profile.set_password('eventauthtest123')
        cls.profile.save()

    def setUp(self):
        self.vatrate = models.VatRate.objects.create(start_at='2014-03-05', rate=0.20, comment='test1')
        venue = models.Venue.objects.create(name='Authorisation Test Venue')
        client = models.Person.objects.create(name='Authorisation Test Person', email='authorisation@functional.test')
        organisation = models.Organisation.objects.create(name='Authorisation Test Organisation', union_account=False)
        self.event = models.Event.objects.create(
            name='Authorisation Test',
            start_date=date.today(),
            venue=venue,
            person=client,
            organisation=organisation,
        )
        self.url = reverse('event_authorise_request', kwargs={'pk': self.event.pk})

    def test_email_check(self):
        self.profile.email = 'teccie@someotherdomain.com'
        self.profile.save()

        self.assertTrue(self.client.login(username=self.profile.username, password='eventauthtest123'))
        
        response = self.client.post(self.url)

        self.assertContains(response, 'must have an @nottinghamtec.co.uk email address')

    def test_request_send(self):
        self.assertTrue(self.client.login(username=self.profile.username, password='eventauthtest123'))
        response = self.client.post(self.url)
        self.assertContains(response, 'This field is required.')

        mail.outbox = []

        response = self.client.post(self.url, {'email': 'client@functional.test'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertIn('client@functional.test', email.to)
        self.assertIn('/event/%d/' % (self.event.pk), email.body)

        # Check sent by details are populated
        self.event.refresh_from_db()
        self.assertEqual(self.event.auth_request_by, self.profile)
        self.assertEqual(self.event.auth_request_to, 'client@functional.test')
        self.assertIsNotNone(self.event.auth_request_at)

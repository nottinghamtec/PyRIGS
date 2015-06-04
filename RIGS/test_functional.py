# -*- coding: utf-8 -*-
from django.test import LiveServerTestCase
from django.core import mail
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from RIGS import models
import re
import os
import json


class UserRegistrationTest(LiveServerTestCase):

    def setUp(self):
        self.browser = webdriver.Firefox()
        os.environ['RECAPTCHA_TESTING'] = 'True'

    def tearDown(self):
        self.browser.quit()
        os.environ['RECAPTCHA_TESTING'] = 'False'

    def test_registration(self):
        # Navigate to the registration page
        self.browser.get(self.live_server_url + '/user/register/')
        # self.browser.implicitly_wait(3)
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
        self.assertIn('activation required', email.subject)
        urls = re.findall(
            'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', email.message)
        self.assertEqual(len(urls), 2)

        mail.outbox = []  # empty this for later

        # Follow link
        self.browser.get(urls[1])  # go to the second link

        # Complete registration
        title_text = self.browser.find_element_by_tag_name('h2')
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
        password.send_keys(Keys.ENTER)
        self.browser.execute_script(
            "return jQuery('#g-recaptcha-response').val('PASSED')")

        # Check we are logged in
        udd = self.browser.find_element_by_id('userdropdown')
        self.assertIn('Hi John', udd)

        # All is well


class EventTest(LiveServerTestCase):

    def setUp(self):
        self.profile = models.Profile(
            username="EventTest", first_name="Event", last_name="Test", initials="ETU", is_superuser=True)
        self.profile.set_password("EventTestPassword")
        self.profile.save()

        self.browser = webdriver.Firefox()
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
        self.browser.execute_script(
            "return jQuery('#g-recaptcha-response').val('PASSED')")
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
        # Requests address
        self.browser.get(self.live_server_url + '/event/create/')
        # Gets redirected to login and back
        self.authenticate('/event/create/')

        # Check has slided up correctly - third save button hidden
        save = self.browser.find_element_by_xpath(
            '(//button[@type="submit"])[3]')
        self.assertFalse(save.is_displayed())

        # Click Rig button
        self.browser.find_element_by_xpath('//button[.="Rig"]').click()

        # Slider expands and save button visible
        self.assertTrue(save.is_displayed())
        form = self.browser.find_element_by_tag_name('form')

        # Create new person
        add_person_button = self.browser.find_element_by_xpath(
            '//a[@data-target="#id_person" and contains(@href, "add")]')
        add_person_button.click()

        # See modal has opened
        modal = self.browser.find_element_by_id('modal')
        self.browser.implicitly_wait(3)
        self.assertTrue(modal.is_displayed())
        self.assertIn("Add Person", modal.find_element_by_tag_name('h3').text)

        # Fill person form out and submit
        modal.find_element_by_xpath(
            '//div[@id="modal"]//input[@id="id_name"]').send_keys("Test Person 1")
        modal.find_element_by_xpath(
            '//div[@id="modal"]//input[@type="submit"]').click()
        self.browser.implicitly_wait(3)
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
        add_person_button.click()

        self.browser.implicitly_wait(3)
        self.assertTrue(modal.is_displayed())
        self.assertIn("Add Person", modal.find_element_by_tag_name('h3').text)

        modal.find_element_by_xpath(
            '//div[@id="modal"]//input[@id="id_name"]').send_keys("Test Person 2")
        modal.find_element_by_xpath(
            '//div[@id="modal"]//input[@type="submit"]').click()
        self.browser.implicitly_wait(3)
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
        self.browser.implicitly_wait(3)
        self.assertTrue(modal.is_displayed())
        self.assertIn("Edit Person", modal.find_element_by_tag_name('h3').text)
        name = modal.find_element_by_xpath(
            '//div[@id="modal"]//input[@id="id_name"]')
        self.assertEqual(person1.name, name.get_attribute('value'))
        name.clear()
        name.send_keys('Rig ' + person1.name)
        name.send_keys(Keys.ENTER)
        self.browser.implicitly_wait(3)
        self.assertFalse(modal.is_displayed())
        person1 = models.Person.objects.get(pk=person1.pk)
        self.assertEqual(person1.name, form.find_element_by_xpath(
            '//button[@data-id="id_person"]/span').text)

        # Create organisation
        add_button = self.browser.find_element_by_xpath(
            '//a[@data-target="#id_organisation" and contains(@href, "add")]')
        add_button.click()
        modal = self.browser.find_element_by_id('modal')
        self.browser.implicitly_wait(3)
        self.assertTrue(modal.is_displayed())
        self.assertIn("Add Organisation", modal.find_element_by_tag_name('h3').text)
        modal.find_element_by_xpath(
            '//div[@id="modal"]//input[@id="id_name"]').send_keys("Test Organisation")
        modal.find_element_by_xpath(
            '//div[@id="modal"]//input[@type="submit"]').click()
        
        # See it is selected
        self.browser.implicitly_wait(3)
        self.assertFalse(modal.is_displayed())
        obj = models.Organisation.objects.get(name="Test Organisation")
        self.assertEqual(obj.name, form.find_element_by_xpath(
            '//button[@data-id="id_organisation"]/span').text)
        # and backend
        option = form.find_element_by_xpath(
            '//select[@id="id_organisation"]//option[@selected="selected"]')
        self.assertEqual(obj.pk, int(option.get_attribute("value")))

        # Create veneue
        add_button = self.browser.find_element_by_xpath(
            '//a[@data-target="#id_venue" and contains(@href, "add")]')
        add_button.click()
        modal = self.browser.find_element_by_id('modal')
        self.browser.implicitly_wait(3)
        self.assertTrue(modal.is_displayed())
        self.assertIn("Add Venue", modal.find_element_by_tag_name('h3').text)
        modal.find_element_by_xpath(
            '//div[@id="modal"]//input[@id="id_name"]').send_keys("Test Venue")
        modal.find_element_by_xpath(
            '//div[@id="modal"]//input[@type="submit"]').click()
        
        # See it is selected
        self.browser.implicitly_wait(3)
        self.assertFalse(modal.is_displayed())
        obj = models.Venue.objects.get(name="Test Venue")
        self.assertEqual(obj.name, form.find_element_by_xpath(
            '//button[@data-id="id_venue"]/span').text)
        # and backend
        option = form.find_element_by_xpath(
            '//select[@id="id_venue"]//option[@selected="selected"]')
        self.assertEqual(obj.pk, int(option.get_attribute("value")))

        # Set start date/time
        form.find_element_by_id('id_start_date').send_keys('3015-05-25')
        form.find_element_by_id('id_start_time').send_keys('06:59')

        # Set end date/time
        form.find_element_by_id('id_end_date').send_keys('4000-06-27')
        form.find_element_by_id('id_end_time').send_keys('07:00')

        # Add item
        form.find_element_by_xpath('//button[contains(@class, "item-add")]').click()
        self.browser.implicitly_wait(3)
        modal = self.browser.find_element_by_id("itemModal")
        modal.find_element_by_id("item_name").send_keys("Test Item 1")
        modal.find_element_by_id("item_description").send_keys("This is an item description\nthat for reasons unkown spans two lines")
        e = modal.find_element_by_id("item_quantity")
        e.click()
        e.send_keys(Keys.UP)
        e.send_keys(Keys.UP)
        e = modal.find_element_by_id("item_cost")
        e.send_keys("23.95")
        e.send_keys(Keys.ENTER) # enter submit

        # Confirm item has been saved to json field
        objectitems = self.browser.execute_script("return objectitems;")
        self.assertEqual(1, len(objectitems))
        testitem = objectitems["-1"]['fields'] # as we are deliberately creating this we know the ID
        self.assertEqual("Test Item 1", testitem['name'])
        self.assertEqual("2", testitem['quantity']) # test a couple of "worse case" fields

        # See new item appear in table
        row = self.browser.find_element_by_id('item--1') # ID number is known, see above
        self.assertIn("Test Item 1", row.find_element_by_xpath('//span[@class="name"]').text)
        self.assertIn("This is an item description", row.find_element_by_xpath('//div[@class="item-description"]').text)
        self.assertEqual(u'£ 23.95', row.find_element_by_xpath('//tr[@id="item--1"]/td[2]').text)
        self.assertEqual("2", row.find_element_by_xpath('//td[@class="quantity"]').text)
        self.assertEqual(u'£ 47.90', row.find_element_by_xpath('//tr[@id="item--1"]/td[4]').text)

        # Check totals
        self.assertEqual("47.90", self.browser.find_element_by_id('sumtotal').text)
        self.assertIn("TBD%", self.browser.find_element_by_id('vat-rate').text)
        self.assertEqual("0.00", self.browser.find_element_by_id('vat').text)
        self.assertEqual("47.90", self.browser.find_element_by_id('total').text)

        # Attempt to save - missing title
        save.click()

        # See error and all data preserved
        error = self.browser.find_element_by_xpath('//div[contains(@class, "alert-danger")]')
        self.assertTrue(error.is_displayed())
        # Should only have one error message
        self.assertEqual("Name", error.find_element_by_xpath('//dt[1]').text)
        self.assertEqual("This field is required.", error.find_element_by_xpath('//dd[1]/ul/li').text)
        # don't need error so close it
        error.find_element_by_xpath('//button[@class="close"]').click()
        self.assertFalse(error.is_displayed())

        # Set title

        # Save again

        # See redirected to success page

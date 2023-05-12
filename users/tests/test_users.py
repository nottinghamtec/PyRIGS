import os
import re
import time

from django.core import mail
from django.test import LiveServerTestCase
from django.test.utils import override_settings
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By

from PyRIGS.tests.base import create_browser
from RIGS import models


# Functional Tests
class UserRegistrationTest(LiveServerTestCase):
    def setUp(self):
        self.browser = create_browser()
        self.browser.implicitly_wait(5)  # Set implicit wait session wide

    def tearDown(self):
        self.browser.quit()

    @override_settings(DEBUG=True)
    def test_registration(self):
        # Navigate to the registration page
        self.browser.get(self.live_server_url + '/user/register/')
        title_text = self.browser.find_element(By.TAG_NAME, 'h3').text
        self.assertIn("User Registration", title_text)

        # Check the form invites correctly
        username = self.browser.find_element(By.ID, 'id_username')
        self.assertEqual(username.get_attribute('placeholder'), 'Username')
        email = self.browser.find_element(By.ID, 'id_email')
        self.assertEqual(email.get_attribute('placeholder'), 'E-mail')
        # If this is correct we don't need to test it later
        self.assertEqual(email.get_attribute('type'), 'email')
        password1 = self.browser.find_element(By.ID, 'id_password1')
        self.assertEqual(password1.get_attribute('placeholder'), 'Password')
        self.assertEqual(password1.get_attribute('type'), 'password')
        password2 = self.browser.find_element(By.ID, 'id_password2')
        self.assertEqual(
            password2.get_attribute('placeholder'), 'Password confirmation')
        self.assertEqual(password2.get_attribute('type'), 'password')
        first_name = self.browser.find_element(By.ID, 'id_first_name')
        self.assertEqual(first_name.get_attribute('placeholder'), 'First name')
        last_name = self.browser.find_element(By.ID, 'id_last_name')
        self.assertEqual(last_name.get_attribute('placeholder'), 'Last name')
        initials = self.browser.find_element(By.ID, 'id_initials')
        self.assertEqual(initials.get_attribute('placeholder'), 'Initials')
        # No longer required for new users
        # phone = self.browser.find_element(By.ID, 'id_phone')
        # self.assertEqual(phone.get_attribute('placeholder'), 'Phone')

        # Fill the form out incorrectly
        username.send_keys('TestUsername')
        email.send_keys('test@example.com')
        password1.send_keys('correcthorsebatterystaple')
        # deliberate mistake
        password2.send_keys('correcthorsebatterystapleerror')
        first_name.send_keys('John')
        last_name.send_keys('Smith')
        initials.send_keys('JS')
        # phone.send_keys('0123456789')
        time.sleep(1)
        self.browser.switch_to.frame(self.browser.find_element(By.TAG_NAME, "iframe"))
        self.browser.find_element(By.ID, 'anchor').click()
        self.browser.switch_to.default_content()
        time.sleep(3)
        # Submit incorrect form
        submit = self.browser.find_element(By.XPATH, "//input[@type='submit']")
        submit.click()

        # Restablish error fields
        password1 = self.browser.find_element(By.ID, 'id_password1')
        password2 = self.browser.find_element(By.ID, 'id_password2')

        # Read what the error is
        alert = self.browser.find_element(By.CSS_SELECTOR, '.alert-danger').text
        # TODO Use regex matching to handle smart/unsmart quotes...
        self.assertIn("password fields didn", alert)

        # Passwords should be empty
        self.assertEqual(password1.get_attribute('value'), '')
        self.assertEqual(password2.get_attribute('value'), '')

        # Correct error
        password1.send_keys('correcthorsebatterystaple')
        password2.send_keys('correcthorsebatterystaple')

        # Submit again
        password2.send_keys(Keys.ENTER)

        # Check we have a success message
        alert = self.browser.find_element(By.CSS_SELECTOR, '.alert-success').text
        self.assertIn('register', alert)
        self.assertIn('email', alert)

        # Check Email
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertIn('John Smith "JS" activation required', email.subject)
        urls = re.findall(
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', email.body)
        self.assertEqual(len(urls), 1)

        mail.outbox = []  # empty this for later

        # Follow link
        self.browser.get(urls[0])  # go to the first link

        # Complete registration
        title_text = self.browser.find_element(By.TAG_NAME, 'h2').text
        self.assertIn('Complete', title_text)

        # Test login
        self.browser.get(self.live_server_url + '/user/login')
        username = self.browser.find_element(By.ID, 'id_username')
        self.assertEqual(username.get_attribute('placeholder'), 'Username')
        password = self.browser.find_element(By.ID, 'id_password')
        self.assertEqual(password.get_attribute('placeholder'), 'Password')
        self.assertEqual(password.get_attribute('type'), 'password')

        # Expected to fail as not approved
        username.send_keys('TestUsername')
        password.send_keys('correcthorsebatterystaple')
        password.send_keys(Keys.ENTER)

        # Test approval
        profileObject = models.Profile.objects.all()[0]
        self.assertFalse(profileObject.is_approved)

        # Read what the error is
        alert = self.browser.find_element(By.CSS_SELECTOR, 'div.alert-danger').text
        self.assertIn("approved", alert)

        # Approve the user so we can proceed
        profileObject.is_approved = True
        profileObject.save()

        # Retry login
        self.browser.get(self.live_server_url + '/user/login')
        username = self.browser.find_element(By.ID, 'id_username')
        username.send_keys('TestUsername')
        password = self.browser.find_element(By.ID, 'id_password')
        password.send_keys('correcthorsebatterystaple')
        password.send_keys(Keys.ENTER)

        # Check we are logged in
        udd = self.browser.find_element(By.CLASS_NAME, 'navbar').text
        self.assertIn('Hi John', udd)

        # Check all the data actually got saved
        self.assertEqual(profileObject.username, 'TestUsername')
        self.assertEqual(profileObject.first_name, 'John')
        self.assertEqual(profileObject.last_name, 'Smith')
        self.assertEqual(profileObject.initials, 'JS')
        # self.assertEqual(profileObject.phone, '0123456789')
        self.assertEqual(profileObject.email, 'test@example.com')

        # All is well

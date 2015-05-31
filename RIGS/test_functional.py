from django.test import LiveServerTestCase
from django.core import mail
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import re
import os

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
		self.browser.implicitly_wait(3)
		title_text = self.browser.find_element_by_tag_name('h3').text
		self.assertIn("User Registration", tilte_text)
		
		# Check the form invites correctly
		username = self.browser.find_element_by_id('id_username')
		self.assertEqual(username.get_attribute('placeholder'), 'Username')
		email = self.browser.find_element_by_id('id_email')
		self.assertEqual(email.get_attribute('placeholder'), 'E-mail')
		self.assertEqual(email.get_attribute('type'), 'email') # If this is correct we don't need to test it later
		password1 = self.browser.find_element_by_id('id_password1')
		self.assertEqual(password1.get_attribute('placeholder'), 'Password')
		self.assertEqual(password1.get_attribute('type'), 'password')
		password2 = self.browser.find_element_by_id('id_password2')
		self.assertEqual(password2.get_attribute('placeholder'), 'Password (again)')
		self.assertEqual(password2.get_attribute('type'), 'password')
		first_name = self.browser.find_element_by_id('id_first_name')
		self.assertEqual(first_name.get_attribute('placeholder'), 'First name')
		last_name = self.browser.find_element_by_id('id_last_name')
		self.assertEqual(last_name.get_attribute('placeholder'), 'Last name')
		initials = self.browser.find_element_by_id('id_initials')
		self.assertEqual(initials.get_attribute('placeholder'), 'Initials')
		phone = self.browser.find_element_by_id('id_phone')
		self.assertEqual(phone.get_attribute('placeholder'), 'Phone')
		captcha = self.browser.find_element_by_id('g-recaptcha-response')
		
		# Fill the form out incorrectly
		username.send_keys('TestUsername')
		email.send_keys('test@example.com')
		password1.send_keys('correcthorsebatterystaple')
		password2.send_keys('correcthorsebatterystapleerror') # deliberate mistake
		first_name.send_keys('John')
		last_name.send_keys('Smith')
		initials.send_keys('JS')
		phone.send_keys('0123456789')
		captcha.send_keys('PASSED')

		# Submit incorrect form
		submit = self.browser.find_element_by_xpath("//input[@type='submit']")
		submit.click()
		# Restablish error fields
		password1 = self.browser.find_element_by_id('id_password1')
		password2 = self.browser.find_element_by_id('id_password2')
		captcha = self.browser.find_element_by_id('g-recaptcha-response')

		# Read what the error is
		alert = self.browser.find_element_by_css_selector('div.alert-danger').text
		self.assertIn("password fields didn't match", alert)

		# Passwords should be empty
		self.assertEqual(password1.get_attribute('value'), '')
		self.assertEqual(password2.get_attribute('value'), '')

		# Correct error
		password1.send_keys('correcthorsebatterystaple')
		password2.send_keys('correcthorsebatterystaple')
		captcha.send_keys('PASSED')

		# Submit again
		password2.send_keys(Keys.ENTER)

		# Check we have a success message
		alert = self.browser.find_element_by_css_selector('div.alert-success').text
		self.assertIn('register', alert)
		self.assertIn('email', alert)

		# Check Email
		self.assertEqual(len(mail.outbox), 1)
		email = mail.outbox[0]
		self.assertIn(email.subject, 'TestUsername activation required')
		urls = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', email.message)
		self.assertEqual(len(urls), 2)

		mail.outbox = [] # empty this for later

		# Follow link
		self.browser.get(urls[1]) # go to the second link

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
		captcha = self.browser.find_element_by_id('g-recaptcha-response')

		username.send_keys('TestUsername')
		password.send_keys('correcthorsebatterystaple')
		password.send_keys(Keys.ENTER)
		captcha.send_keys('PASSED')

		# Check we are logged in
		udd = self.browser.find_element_by_id('userdropdown')
		self.assertIn('Hi John', udd)

		# All is well

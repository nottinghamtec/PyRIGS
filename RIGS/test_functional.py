from django.test import LiveServerTestCase

from selenium import webdriver

class UserRegistrationTest(LiveServerTestCase):
	def setUp(self):
		self.browser = webdriver.Firefox()

	def tearDown(self):
		self.browser.quit()

	def test_false(self):
		self.assertFail("Finish me")
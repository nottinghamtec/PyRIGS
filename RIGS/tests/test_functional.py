# -*- coding: utf-8 -*-
import os
import re
from datetime import date, time, datetime, timedelta

import pytz
from django.conf import settings
from django.core import mail, signing
from django.db import transaction
from django.http import HttpResponseBadRequest
from django.test import LiveServerTestCase, TestCase
from django.test.client import Client
from django.urls import reverse
from reversion import revisions as reversion
from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait

from RIGS import models

from reversion import revisions as reversion
from django.urls import reverse
from django.core import mail, signing
from PyRIGS.tests.base import create_browser, animation_is_finished
from django.conf import settings

import sys


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


class SearchTest(LiveServerTestCase):
    def setUp(self):
        self.profile = models.Profile(
            username="SearchTest", first_name="Search", last_name="Test", initials="STU", is_superuser=True)
        self.profile.set_password("SearchTestPassword")
        self.profile.save()

        self.vatrate = models.VatRate.objects.create(start_at='2014-03-05', rate=0.20, comment='test1')

        self.browser = create_browser()
        self.browser.implicitly_wait(10)  # Set implicit wait session wide

        os.environ['RECAPTCHA_TESTING'] = 'True'

        models.Event.objects.create(name="Right Event", status=models.Event.PROVISIONAL,
                                    start_date=date.today(),
                                    description="This event is searched for endlessly over and over")
        models.Event.objects.create(name="Wrong Event", status=models.Event.PROVISIONAL, start_date=date.today(),
                                    description="This one should never be found.")

    def tearDown(self):
        self.browser.quit()
        os.environ['RECAPTCHA_TESTING'] = 'False'

    def test_search(self):
        self.browser.get(self.live_server_url)
        username = self.browser.find_element_by_id('id_username')
        password = self.browser.find_element_by_id('id_password')
        submit = self.browser.find_element_by_css_selector(
            'input[type=submit]')

        username.send_keys("SearchTest")
        password.send_keys("SearchTestPassword")
        submit.click()

        form = self.browser.find_element_by_id('searchForm')
        search_box = form.find_element_by_id('id_search_input')
        search_box.send_keys('Right')
        search_box.send_keys(Keys.ENTER)

        event_name = self.browser.find_element_by_xpath(
            '//*[@id="content"]/div[1]/div[4]/div/div/table/tbody/tr[1]/td[3]/h4').text
        self.assertIn('Right', event_name)
        self.assertNotIn('Wrong', event_name)

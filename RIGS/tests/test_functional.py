import datetime
from datetime import date, time, timedelta
from urllib.parse import urlparse

from django.conf import settings
from django.core import mail, signing
from django.core.management import call_command
from django.db import transaction
from django.http import HttpResponseBadRequest
from django.test import TestCase
from django.test.client import Client
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone
from reversion import revisions as reversion
from RIGS import models, urls
from RIGS.tests import regions

from . import pages


class BaseCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.vatrate = models.VatRate.objects.create(start_at='2014-03-05', rate=0.20, comment='test1')
        cls.profile = models.Profile.objects.get_or_create(
            first_name='Test',
            last_name='TEC User',
            username='eventauthtest',
            email='teccie@functional.test',
            is_superuser=True  # lazily grant all permissions
        )[0]

    def setUp(self):
        super().setUp()
        self.profile.set_password('testuser')
        self.profile.save()
        self.assertTrue(self.client.login(username=self.profile.username, password='testuser'))
        venue = models.Venue.objects.create(name='Authorisation Test Venue')
        client = models.Person.objects.create(name='Authorisation Test Person', email='authorisation@functional.test')
        organisation = models.Organisation.objects.create(name='Authorisation Test Organisation', union_account=True)
        self.event = models.Event.objects.create(
            name='Authorisation Test',
            start_date=date.today(),
            venue=venue,
            person=client,
            organisation=organisation,
        )


class TestEventValidation(BaseCase):
    def test_create(self):
        url = reverse('event_create')
        # end time before start access after start
        response = self.client.post(url, {'start_date': datetime.date(2020, 1, 1), 'start_time': datetime.time(10, 00), 'end_time': datetime.time(9, 00), 'access_at': datetime.datetime(2020, 1, 5, 10)})
        self.assertFormError(response, 'form', 'end_time', "Unless you've invented time travel, the event can't finish before it has started.")
        self.assertFormError(response, 'form', 'access_at', "Regardless of what some clients might think, access time cannot be after the event has started.")


class ClientEventAuthorisationTest(BaseCase):
    auth_data = {
        'name': 'Test ABC',
        'po': '1234ABCZXY',
        'account_code': 'ABC TEST 12345',
        'uni_id': 1234567890,
        'tos': True
    }

    def setUp(self):
        super().setUp()
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

    def test_validation(self):
        response = self.client.get(self.url)
        self.assertContains(response, "Terms of Hire")
        self.assertContains(response, "Account code")
        self.assertContains(response, "University ID")

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


class TECEventAuthorisationTest(BaseCase):
    def setUp(self):
        super().setUp()
        self.url = reverse('event_authorise_request', kwargs={'pk': self.event.pk})

    def test_email_check(self):
        self.profile.email = 'teccie@someotherdomain.com'
        self.profile.save()

        response = self.client.post(self.url)

        self.assertContains(response, 'must have an @nottinghamtec.co.uk email address')

    def test_request_send(self):
        self.profile.email = 'teccie@nottinghamtec.co.uk'
        self.profile.save()
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

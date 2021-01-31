import datetime
from datetime import date

import pytest
from django.conf import settings
from django.core import mail, signing
from django.http import HttpResponseBadRequest
from django.test import TestCase
from django.urls import reverse

from RIGS import models
from pytest_django.asserts import assertContains, assertNotContains


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
        response = self.client.post(url, {'start_date': datetime.date(2020, 1, 1), 'start_time': datetime.time(10, 00),
                                          'end_time': datetime.time(9, 00),
                                          'access_at': datetime.datetime(2020, 1, 5, 10)})
        self.assertFormError(response, 'form', 'end_time',
                             "Unless you've invented time travel, the event can't finish before it has started.")
        self.assertFormError(response, 'form', 'access_at',
                             "Regardless of what some clients might think, access time cannot be after the event has started.")


def setup_event():
    models.VatRate.objects.create(start_at='2014-03-05', rate=0.20, comment='test1')
    venue = models.Venue.objects.create(name='Authorisation Test Venue')
    client = models.Person.objects.create(name='Authorisation Test Person', email='authorisation@functional.test')
    organisation = models.Organisation.objects.create(name='Authorisation Test Organisation', union_account=True)
    return models.Event.objects.create(
        name='Authorisation Test',
        start_date=date.today(),
        venue=venue,
        person=client,
        organisation=organisation,
    )


def setup_mail(event, profile):
    profile.email = "teccie@nottinghamtec.co.uk"
    profile.save()
    auth_data = {
        'name': 'Test ABC',
        'po': '1234ABCZXY',
        'account_code': 'ABC TEST 12345',
        'uni_id': 1234567890,
        'tos': True
    }
    hmac = signing.dumps({'pk': event.pk, 'email': 'authemail@function.test',
                          'sent_by': profile.pk})
    url = reverse('event_authorise', kwargs={'pk': event.pk, 'hmac': hmac})
    return auth_data, hmac, url


def test_requires_valid_hmac(client, admin_user):
    event = setup_event()
    auth_data, hmac, url = setup_mail(event, admin_user)
    bad_hmac = hmac[:-1]
    url = reverse('event_authorise', kwargs={'pk': event.pk, 'hmac': bad_hmac})
    response = client.get(url)
    assert isinstance(response, HttpResponseBadRequest)
    # TODO: Add some form of sensible user facing error
    # self.assertIn(response.content, "new URL")  # check there is some level of sane instruction
    # response = client.get(url)
    # assertContains(response, event.organisation.name)


def test_validation(client, admin_user):
    event = setup_event()
    auth_data, hmac, url = setup_mail(event, admin_user)
    response = client.get(url)
    assertContains(response, "Terms of Hire")
    assertContains(response, "Account code")
    assertContains(response, "University ID")

    response = client.post(url)
    assertContains(response, "This field is required.", 5)

    auth_data['amount'] = event.total + 1

    response = client.post(url, auth_data)
    assertContains(response, "The amount authorised must equal the total for the event")
    assertNotContains(response, "This field is required.")

    auth_data['amount'] = event.total
    response = client.post(url, auth_data)
    assertContains(response, "Your event has been authorised")

    event.refresh_from_db()
    assert event.authorised
    assert str(event.authorisation.email) == "authemail@function.test"


def test_duplicate_warning(client, admin_user):
    event = setup_event()
    auth_data, hmac, url = setup_mail(event, admin_user)
    auth = models.EventAuthorisation.objects.create(event=event, name='Test ABC', email='dupe@functional.test',
                                                    amount=event.total, sent_by=admin_user)
    response = client.get(url)
    assertContains(response, 'This event has already been authorised.')

    auth.amount += 1
    auth.save()

    response = client.get(url)
    assertContains(response, 'amount has changed')


@pytest.mark.django_db(transaction=True)
def test_email_sent(admin_client, admin_user, mailoutbox):
    event = setup_event()
    auth_data, hmac, url = setup_mail(event, admin_user)

    data = auth_data
    data['amount'] = event.total
    response = admin_client.post(url, data)
    assertContains(response, "Your event has been authorised.")
    assert len(mailoutbox) == 2
    assert mailoutbox[0].to == ['authemail@function.test']
    assert mailoutbox[1].to == [settings.AUTHORISATION_NOTIFICATION_ADDRESS]


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

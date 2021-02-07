import datetime
from datetime import date

import pytest
from django.conf import settings
from django.core import mail, signing
from django.http import HttpResponseBadRequest
from django.test import TestCase
from django.urls import reverse

import PyRIGS.tests.base
from RIGS import models
from pytest_django.asserts import assertContains, assertNotContains, assertFormError


def setup_event():
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


def test_create(admin_client):
    url = reverse('event_create')
    # end time before start access after start
    response = admin_client.post(url, {'start_date': datetime.date(2020, 1, 1), 'start_time': datetime.time(10, 00),
                                       'end_time': datetime.time(9, 00),
                                       'access_at': datetime.datetime(2020, 1, 5, 10)})
    assertFormError(response, 'form', 'end_time',
                    "Unless you've invented time travel, the event can't finish before it has started.")
    assertFormError(response, 'form', 'access_at',
                    "Regardless of what some clients might think, access time cannot be after the event has started.")


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


@pytest.mark.django_db
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


def test_email_check(admin_client, admin_user):
    event = setup_event()
    url = reverse('event_authorise_request', kwargs={'pk': event.pk})
    admin_user.email = 'teccie@someotherdomain.com'
    admin_user.save()

    response = admin_client.post(url)

    assertContains(response, 'must have an @nottinghamtec.co.uk email address')


def test_request_send(admin_client, admin_user):
    event = setup_event()
    url = reverse('event_authorise_request', kwargs={'pk': event.pk})
    admin_user.email = 'teccie@nottinghamtec.co.uk'
    admin_user.save()
    response = admin_client.post(url)
    assertContains(response, 'This field is required.')

    mail.outbox = []

    response = admin_client.post(url, {'email': 'client@functional.test'})
    assert response.status_code == 302
    assert len(mail.outbox) == 1
    email = mail.outbox[0]
    assert 'client@functional.test' in email.to
    assert '/event/%d/' % event.pk in email.body

    # Check sent by details are populated
    event.refresh_from_db()
    assert event.auth_request_by == admin_user
    assert event.auth_request_to == 'client@functional.test'
    assert event.auth_request_at is not None

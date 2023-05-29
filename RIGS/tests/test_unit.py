import os
import pytest
from datetime import date

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.test import TestCase
from django.test.utils import override_settings
from django.utils.safestring import SafeText
from RIGS.templatetags.markdown_tags import markdown_filter
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from pytest_django.asserts import assertRedirects, assertNotContains, assertContains

from PyRIGS.tests.base import assert_times_almost_equal, assert_oembed, login
from RIGS import models

pytestmark = pytest.mark.django_db


class TestAdminMergeObjects(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.profile = models.Profile.objects.create(username="testuser1", email="1@test.com", is_superuser=True,
                                                    is_active=True, is_staff=True)
        cls.persons = {
            1: models.Person.objects.create(name="Person 1"),
            2: models.Person.objects.create(name="Person 2"),
            3: models.Person.objects.create(name="Person 3"),
        }

        cls.organisations = {
            1: models.Organisation.objects.create(name="Organisation 1"),
            2: models.Organisation.objects.create(name="Organisation 2"),
            3: models.Organisation.objects.create(name="Organisation 3"),
        }

        cls.venues = {
            1: models.Venue.objects.create(name="Venue 1"),
            2: models.Venue.objects.create(name="Venue 2"),
            3: models.Venue.objects.create(name="Venue 3"),
        }

        cls.events = {
            1: models.Event.objects.create(name="TE E1", start_date=date.today(), person=cls.persons[1],
                                           organisation=cls.organisations[3], venue=cls.venues[2]),
            2: models.Event.objects.create(name="TE E2", start_date=date.today(), person=cls.persons[2],
                                           organisation=cls.organisations[2], venue=cls.venues[3]),
            3: models.Event.objects.create(name="TE E3", start_date=date.today(), person=cls.persons[3],
                                           organisation=cls.organisations[1], venue=cls.venues[1]),
            4: models.Event.objects.create(name="TE E4", start_date=date.today(), person=cls.persons[3],
                                           organisation=cls.organisations[3], venue=cls.venues[3]),
        }

    def setUp(self):
        self.profile.set_password('testuser')
        self.profile.save()
        self.assertTrue(self.client.login(username=self.profile.username, password='testuser'))

    def test_merge_confirmation(self):
        change_url = reverse('admin:RIGS_venue_changelist')
        data = {
            'action': 'merge',
            '_selected_action': [str(val.pk) for key, val in self.venues.items()]

        }
        response = self.client.post(change_url, data, follow=True)

        self.assertContains(response, "The following objects will be merged")
        for key, venue in self.venues.items():
            self.assertContains(response, venue.name)

    def test_merge_no_master(self):
        change_url = reverse('admin:RIGS_venue_changelist')
        data = {'action': 'merge',
                '_selected_action': [str(val.pk) for key, val in self.venues.items()],
                'post': 'yes',
                }
        response = self.client.post(change_url, data, follow=True)

        self.assertContains(response, "An error occured")

    def test_venue_merge(self):
        change_url = reverse('admin:RIGS_venue_changelist')

        data = {'action': 'merge',
                '_selected_action': [str(self.venues[1].pk), str(self.venues[2].pk)],
                'post': 'yes',
                'master': self.venues[1].pk
                }

        response = self.client.post(change_url, data, follow=True)
        self.assertContains(response, "Objects successfully merged")
        self.assertContains(response, self.venues[1].name)

        # Check the master copy still exists
        self.assertTrue(models.Venue.objects.get(pk=self.venues[1].pk))

        # Check the un-needed venue has been disposed of
        self.assertRaises(ObjectDoesNotExist, models.Venue.objects.get, pk=self.venues[2].pk)

        # Check the one we didn't delete is still there
        self.assertEqual(models.Venue.objects.get(pk=self.venues[3].pk), self.venues[3])

        # Check the events have been moved to the master venue
        for key, event in self.events.items():
            updatedEvent = models.Event.objects.get(pk=event.pk)
            if event.venue == self.venues[3]:  # The one we left in place
                continue
            self.assertEqual(updatedEvent.venue, self.venues[1])

    def test_person_merge(self):
        change_url = reverse('admin:RIGS_person_changelist')

        data = {'action': 'merge',
                '_selected_action': [str(self.persons[1].pk), str(self.persons[2].pk)],
                'post': 'yes',
                'master': self.persons[1].pk
                }

        response = self.client.post(change_url, data, follow=True)
        self.assertContains(response, "Objects successfully merged")
        self.assertContains(response, self.persons[1].name)

        # Check the master copy still exists
        self.assertTrue(models.Person.objects.get(pk=self.persons[1].pk))

        # Check the un-needed people have been disposed of
        self.assertRaises(ObjectDoesNotExist, models.Person.objects.get, pk=self.persons[2].pk)

        # Check the one we didn't delete is still there
        self.assertEqual(models.Person.objects.get(pk=self.persons[3].pk), self.persons[3])

        # Check the events have been moved to the master person
        for key, event in self.events.items():
            updatedEvent = models.Event.objects.get(pk=event.pk)
            if event.person == self.persons[3]:  # The one we left in place
                continue
            self.assertEqual(updatedEvent.person, self.persons[1])

    def test_organisation_merge(self):
        change_url = reverse('admin:RIGS_organisation_changelist')

        data = {'action': 'merge',
                '_selected_action': [str(self.organisations[1].pk), str(self.organisations[2].pk)],
                'post': 'yes',
                'master': self.organisations[1].pk
                }

        response = self.client.post(change_url, data, follow=True)
        self.assertContains(response, "Objects successfully merged")
        self.assertContains(response, self.organisations[1].name)

        # Check the master copy still exists
        self.assertTrue(models.Organisation.objects.get(pk=self.organisations[1].pk))

        # Check the un-needed organisations have been disposed of
        self.assertRaises(ObjectDoesNotExist, models.Organisation.objects.get, pk=self.organisations[2].pk)

        # Check the one we didn't delete is still there
        self.assertEqual(models.Organisation.objects.get(pk=self.organisations[3].pk), self.organisations[3])

        # Check the events have been moved to the master organisation
        for key, event in self.events.items():
            updatedEvent = models.Event.objects.get(pk=event.pk)
            if event.organisation == self.organisations[3]:  # The one we left in place
                continue
            self.assertEqual(updatedEvent.organisation, self.organisations[1])


class TestInvoiceDelete(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.profile = models.Profile.objects.create(username="testuser1", email="1@test.com", is_superuser=True,
                                                    is_active=True, is_staff=True)
        cls.vatrate = models.VatRate.objects.create(start_at='2014-03-05', rate=0.20, comment='test1')
        cls.events = {
            1: models.Event.objects.create(name="TE E1", start_date=date.today()),
            2: models.Event.objects.create(name="TE E2", start_date=date.today())
        }

        cls.invoices = {
            1: models.Invoice.objects.create(event=cls.events[1]),
            2: models.Invoice.objects.create(event=cls.events[2])
        }

        cls.payments = {
            1: models.Payment.objects.create(invoice=cls.invoices[1], date=date.today(), amount=12.34,
                                             method=models.Payment.CASH)
        }

    def setUp(self):
        self.profile.set_password('testuser')
        self.profile.save()
        self.assertTrue(self.client.login(username=self.profile.username, password='testuser'))

    def test_invoice_delete_allowed(self):
        request_url = reverse('invoice_delete', kwargs={'pk': self.invoices[2].pk})

        response = self.client.get(request_url, follow=True)
        self.assertContains(response, "Are you sure")

        # Check the invoice still exists
        self.assertTrue(models.Invoice.objects.get(pk=self.invoices[2].pk))

        # Actually delete it
        self.client.post(request_url, follow=True)

        # Check the invoice is deleted
        self.assertRaises(ObjectDoesNotExist, models.Invoice.objects.get, pk=self.invoices[2].pk)

    def test_invoice_delete_not_allowed(self):
        request_url = reverse('invoice_delete', kwargs={'pk': self.invoices[1].pk})

        response = self.client.get(request_url, follow=True)
        self.assertContains(response, "To delete an invoice, delete the payments first.")

        # Check the invoice still exists
        self.assertTrue(models.Invoice.objects.get(pk=self.invoices[1].pk))

        # Try to actually delete it
        self.client.post(request_url, follow=True)

        # Check this didn't work
        self.assertTrue(models.Invoice.objects.get(pk=self.invoices[1].pk))


class TestPrintPaperwork(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.profile = models.Profile.objects.create(username="testuser1", email="1@test.com", is_superuser=True,
                                                    is_active=True, is_staff=True)
        cls.events = {
            1: models.Event.objects.create(name="TE E1", start_date=date.today(),
                                           description="This is an event description\nthat for a very specific reason spans two lines."),
        }

        cls.invoices = {
            1: models.Invoice.objects.create(event=cls.events[1]),
        }

    def setUp(self):
        self.profile.set_password('testuser')
        self.profile.save()
        self.assertTrue(self.client.login(username=self.profile.username, password='testuser'))

    def test_print_paperwork_success(self):
        request_url = reverse('event_print', kwargs={'pk': self.events[1].pk})

        response = self.client.get(request_url, follow=True)
        self.assertEqual(response.status_code, 200)

    def test_print_invoice_success(self):
        request_url = reverse('invoice_print', kwargs={'pk': self.invoices[1].pk})

        response = self.client.get(request_url, follow=True)
        self.assertEqual(response.status_code, 200)


def test_login_redirect(client, django_user_model):
    request_url = reverse('event_embed', kwargs={'pk': 1})
    expected_url = f"{reverse('login_embed')}?next={request_url}"

    # Request the page and check it redirects
    response = client.get(request_url, follow=True)
    assertRedirects(response, expected_url, status_code=302, target_status_code=200)

    # Now login
    login(client, django_user_model)

    # And check that it no longer redirects
    response = client.get(request_url, follow=True)
    assert len(response.redirect_chain) == 0


def test_login_cookie_warning(client):
    login_url = reverse('login_embed')
    response = client.post(login_url, follow=True)
    assertContains(response, "Cookies do not seem to be enabled")


def test_xframe_headers(admin_client, basic_event):
    event_url = reverse('event_embed', kwargs={'pk': basic_event.pk})
    login_url = reverse('login_embed')

    response = admin_client.get(event_url, follow=True)
    with pytest.raises(KeyError):
        response.headers["X-Frame-Options"]

    response = admin_client.get(login_url, follow=True)
    with pytest.raises(KeyError):
        response.headers["X-Frame-Options"]


def test_oembed(client, basic_event):
    event_url = reverse('event_detail', kwargs={'pk': basic_event.pk})
    event_embed_url = reverse('event_embed', kwargs={'pk': basic_event.pk})
    oembed_url = reverse('event_oembed', kwargs={'pk': basic_event.pk})

    alt_oembed_url = reverse('event_oembed', kwargs={'pk': 999})
    alt_event_embed_url = reverse('event_embed', kwargs={'pk': 999})

    assert_oembed(alt_event_embed_url, alt_oembed_url, client, event_embed_url, event_url, oembed_url)


def search(client, url, found, notfound, arguments):
    for argument in arguments:
        query = getattr(found, argument)
        request_url = "%s?q=%s" % (reverse_lazy(url), query)
        response = client.get(request_url, follow=True)
        assertContains(response, getattr(found, 'name'))
        assertNotContains(response, getattr(notfound, 'name'))


def test_search(admin_client):
    persons = {
        1: models.Person.objects.create(name="Right Person", phone="1234"),
        2: models.Person.objects.create(name="Wrong Person", phone="5678"),
    }
    organisations = {
        1: models.Organisation.objects.create(name="Right Organisation", email="test@example.com"),
        2: models.Organisation.objects.create(name="Wrong Organisation", email="check@fake.co.uk"),
    }
    venues = {
        1: models.Venue.objects.create(name="Right Venue", address="1 Test Street, EX1"),
        2: models.Venue.objects.create(name="Wrong Venue", address="2 Check Way, TS2"),
    }
    events = {
        1: models.Event.objects.create(name="Right Event", start_date=date.today(), venue=venues[1], person=persons[1],
                                       organisation=organisations[1]),
        2: models.Event.objects.create(name="Wrong Event", start_date=date.today(), venue=venues[2], person=persons[2],
                                       organisation=organisations[2]),
    }
    search(admin_client, 'event_archive', events[1], events[2], ['name', 'id'])
    search(admin_client, 'person_list', persons[1], persons[2], ['name', 'id', 'phone'])
    search(admin_client, 'organisation_list', organisations[1], organisations[2],
           ['name', 'id', 'email'])
    search(admin_client, 'venue_list', venues[1], venues[2],
           ['name', 'id', 'address'])


def test_hs_list(admin_client, basic_event):
    request_url = reverse('hs_list')
    response = admin_client.get(request_url, follow=True)
    assertContains(response, basic_event.name)
    # assertContains(response, events[2].name)
    assertContains(response, 'Create')


def review(client, profile, obj, request_url):
    time = timezone.now()
    response = client.get(reverse(request_url, kwargs={'pk': obj.pk}), follow=True)
    obj.refresh_from_db()
    assertContains(response, 'Reviewed by')
    assertContains(response, profile.name)
    assert_times_almost_equal(time, obj.reviewed_at)


def test_ra_review(admin_client, admin_user, ra):
    review(admin_client, admin_user, ra, 'ra_review')


def test_checklist_review(admin_client, admin_user, checklist):
    review(admin_client, admin_user, checklist, 'ec_review')


def test_ra_redirect(admin_client, admin_user, ra):
    request_url = reverse('event_ra', kwargs={'pk': ra.event.pk})
    expected_url = reverse('ra_edit', kwargs={'pk': ra.pk})
    response = admin_client.get(request_url, follow=True)
    assertRedirects(response, expected_url, status_code=302, target_status_code=200)


class TestMarkdownTemplateTags(TestCase):
    with open(os.path.join(settings.BASE_DIR, "RIGS/tests/sample.md"), encoding="utf-8") as f:
        markdown = f.read()

    def test_html_safe(self):
        html = markdown_filter(self.markdown)
        self.assertIsInstance(html, SafeText)

    def test_img_strip(self):
        rml = markdown_filter(self.markdown, 'rml')
        self.assertNotIn("<img", rml)

    def test_code(self):
        rml = markdown_filter(self.markdown, 'rml')
        self.assertIn('<font face="Courier">monospace</font>', rml)

    def test_blockquote(self):
        rml = markdown_filter(self.markdown, 'rml')
        self.assertIn("<pre>\nBlock quotes", rml)

    def test_lists(self):
        rml = markdown_filter(self.markdown, 'rml')
        self.assertIn("<li><para>second item</para></li>", rml)  # <ol>
        self.assertIn("<li><para>that one</para></li>", rml)  # <ul>

    def test_in_print(self):
        event = models.Event.objects.create(
            name="MD Print Test",
            description=self.markdown,
            start_date='2016-01-01',
        )
        event_item = models.EventItem.objects.create(event=event, name="TI I1", quantity=1, cost=1.00, order=1, description="* test \n * test \n * test")
        user = models.Profile.objects.create(
            username='RML test',
            is_superuser=True,  # Don't care about permissions
            is_active=True,
        )
        user.set_password('rmltester')
        user.save()

        self.assertTrue(self.client.login(username=user.username, password='rmltester'))
        response = self.client.get(reverse('event_print', kwargs={'pk': event.pk}))
        self.assertEqual(response.status_code, 200)
        # By the time we have a PDF it should be larger than the original by some margin
        # RML hard fails if something doesn't work
        self.assertGreater(len(response.content), len(self.markdown))

    def test_nonetype(self):
        html = markdown_filter(None)
        self.assertIsNone(html)

    def test_linebreaks(self):
        html = markdown_filter(self.markdown)
        self.assertIn("Itemized lists<br/>\nlook like", html)

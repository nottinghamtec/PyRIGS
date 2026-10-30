import csv
import os
import pytest
from datetime import date, time, timedelta

from django.conf import settings
from django.utils.html import escape
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.test import TestCase
from django.utils.safestring import SafeText
from RIGS.templatetags.markdown_tags import markdown_filter
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from pytest_django.asserts import assertRedirects, assertNotContains, assertContains

from PyRIGS.tests.base import assert_times_almost_equal, assert_oembed, login
from django.forms.models import model_to_dict
from RIGS import finance_stats, forms, models

pytestmark = pytest.mark.django_db


class TestAdminMergeObjects(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.profile = models.Profile.objects.create(
            username="testuser1", email="1@test.com", is_superuser=True, is_active=True, is_staff=True
        )
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
            1: models.Event.objects.create(
                name="TE E1",
                start_date=date.today(),
                person=cls.persons[1],
                organisation=cls.organisations[3],
                venue=cls.venues[2],
            ),
            2: models.Event.objects.create(
                name="TE E2",
                start_date=date.today(),
                person=cls.persons[2],
                organisation=cls.organisations[2],
                venue=cls.venues[3],
            ),
            3: models.Event.objects.create(
                name="TE E3",
                start_date=date.today(),
                person=cls.persons[3],
                organisation=cls.organisations[1],
                venue=cls.venues[1],
            ),
            4: models.Event.objects.create(
                name="TE E4",
                start_date=date.today(),
                person=cls.persons[3],
                organisation=cls.organisations[3],
                venue=cls.venues[3],
            ),
        }

    def setUp(self):
        self.profile.set_password("testuser")
        self.profile.save()
        self.assertTrue(self.client.login(username=self.profile.username, password="testuser"))

    def test_merge_confirmation(self):
        change_url = reverse("admin:RIGS_venue_changelist")
        data = {"action": "merge", "_selected_action": [str(val.pk) for key, val in self.venues.items()]}
        response = self.client.post(change_url, data, follow=True)

        self.assertContains(response, "The following objects will be merged")
        for key, venue in self.venues.items():
            self.assertContains(response, venue.name)

    def test_merge_no_master(self):
        change_url = reverse("admin:RIGS_venue_changelist")
        data = {
            "action": "merge",
            "_selected_action": [str(val.pk) for key, val in self.venues.items()],
            "post": "yes",
        }
        response = self.client.post(change_url, data, follow=True)

        self.assertContains(response, "An error occured")

    def test_venue_merge(self):
        change_url = reverse("admin:RIGS_venue_changelist")

        data = {
            "action": "merge",
            "_selected_action": [str(self.venues[1].pk), str(self.venues[2].pk)],
            "post": "yes",
            "master": self.venues[1].pk,
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
        change_url = reverse("admin:RIGS_person_changelist")

        data = {
            "action": "merge",
            "_selected_action": [str(self.persons[1].pk), str(self.persons[2].pk)],
            "post": "yes",
            "master": self.persons[1].pk,
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
        change_url = reverse("admin:RIGS_organisation_changelist")

        data = {
            "action": "merge",
            "_selected_action": [str(self.organisations[1].pk), str(self.organisations[2].pk)],
            "post": "yes",
            "master": self.organisations[1].pk,
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
        cls.profile = models.Profile.objects.create(
            username="testuser1", email="1@test.com", is_superuser=True, is_active=True, is_staff=True
        )
        cls.vatrate = models.VatRate.objects.create(start_at="2014-03-05", rate=0.20, comment="test1")
        cls.events = {
            1: models.Event.objects.create(name="TE E1", start_date=date.today()),
            2: models.Event.objects.create(name="TE E2", start_date=date.today()),
        }

        cls.invoices = {
            1: models.Invoice.objects.create(event=cls.events[1]),
            2: models.Invoice.objects.create(event=cls.events[2]),
        }

        cls.payments = {
            1: models.Payment.objects.create(
                invoice=cls.invoices[1], date=date.today(), amount=12.34, method=models.Payment.CASH
            )
        }

    def setUp(self):
        self.profile.set_password("testuser")
        self.profile.save()
        self.assertTrue(self.client.login(username=self.profile.username, password="testuser"))

    def test_invoice_delete_allowed(self):
        request_url = reverse("invoice_delete", kwargs={"pk": self.invoices[2].pk})

        response = self.client.get(request_url, follow=True)
        self.assertContains(response, "Are you sure")

        # Check the invoice still exists
        self.assertTrue(models.Invoice.objects.get(pk=self.invoices[2].pk))

        # Actually delete it
        self.client.post(request_url, follow=True)

        # Check the invoice is deleted
        self.assertRaises(ObjectDoesNotExist, models.Invoice.objects.get, pk=self.invoices[2].pk)

    def test_invoice_delete_not_allowed(self):
        request_url = reverse("invoice_delete", kwargs={"pk": self.invoices[1].pk})

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
        cls.profile = models.Profile.objects.create(
            username="testuser1", email="1@test.com", is_superuser=True, is_active=True, is_staff=True
        )
        cls.events = {
            1: models.Event.objects.create(
                name="TE E1",
                start_date=date.today(),
                description="This is an event description\nthat for a very specific reason spans two lines.",
            ),
        }

        cls.invoices = {
            1: models.Invoice.objects.create(event=cls.events[1]),
        }

    def setUp(self):
        self.profile.set_password("testuser")
        self.profile.save()
        self.assertTrue(self.client.login(username=self.profile.username, password="testuser"))

    def test_print_paperwork_success(self):
        request_url = reverse("event_print", kwargs={"pk": self.events[1].pk})

        response = self.client.get(request_url, follow=True)
        self.assertEqual(response.status_code, 200)

    def test_print_invoice_success(self):
        request_url = reverse("invoice_print", kwargs={"pk": self.invoices[1].pk})

        response = self.client.get(request_url, follow=True)
        self.assertEqual(response.status_code, 200)


def test_login_redirect(client, django_user_model):
    request_url = reverse("event_embed", kwargs={"pk": 1})
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
    login_url = reverse("login_embed")
    response = client.post(login_url, follow=True)
    assertContains(response, "Cookies do not seem to be enabled")


def test_xframe_headers(admin_client, basic_event):
    event_url = reverse("event_embed", kwargs={"pk": basic_event.pk})
    login_url = reverse("login_embed")

    response = admin_client.get(event_url, follow=True)
    with pytest.raises(KeyError):
        response.headers["X-Frame-Options"]

    response = admin_client.get(login_url, follow=True)
    with pytest.raises(KeyError):
        response.headers["X-Frame-Options"]


def test_oembed(client, basic_event):
    event_url = reverse("event_detail", kwargs={"pk": basic_event.pk})
    event_embed_url = reverse("event_embed", kwargs={"pk": basic_event.pk})
    oembed_url = reverse("event_oembed", kwargs={"pk": basic_event.pk})

    alt_oembed_url = reverse("event_oembed", kwargs={"pk": 999})
    alt_event_embed_url = reverse("event_embed", kwargs={"pk": 999})

    assert_oembed(alt_event_embed_url, alt_oembed_url, client, event_embed_url, event_url, oembed_url)


def search(client, url, found, notfound, arguments):
    for argument in arguments:
        query = getattr(found, argument)
        request_url = "%s?q=%s" % (reverse_lazy(url), query)
        response = client.get(request_url, follow=True)
        assertContains(response, getattr(found, "name"))
        assertNotContains(response, getattr(notfound, "name"))


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
        1: models.Event.objects.create(
            name="Right Event",
            start_date=date.today(),
            venue=venues[1],
            person=persons[1],
            organisation=organisations[1],
        ),
        2: models.Event.objects.create(
            name="Wrong Event",
            start_date=date.today(),
            venue=venues[2],
            person=persons[2],
            organisation=organisations[2],
        ),
    }
    search(admin_client, "event_archive", events[1], events[2], ["name", "id"])
    search(admin_client, "person_list", persons[1], persons[2], ["name", "id", "phone"])
    search(admin_client, "organisation_list", organisations[1], organisations[2], ["name", "id", "email"])
    search(admin_client, "venue_list", venues[1], venues[2], ["name", "id", "address"])


def test_hs_list(admin_client, basic_event):
    request_url = reverse("hs_list")
    response = admin_client.get(request_url, follow=True)
    assertContains(response, basic_event.name)
    # assertContains(response, events[2].name)
    assertContains(response, "Create")
    assertContains(response, "Legacy version")


def test_hs_list_only_needing_action(admin_client, admin_user, basic_event, ra, venue):
    basic_event.status = models.Event.CONFIRMED
    basic_event.mic = admin_user
    basic_event.save()
    url = reverse("hs_list")

    # Unreviewed RA on a confirmed event: amber, so shown
    assertContains(admin_client.get(url, {"action": 1}), basic_event.name)

    # Reviewed RA with everything else done: green, so hidden
    ra.reviewed_by = admin_user
    ra.save()
    response = admin_client.get(url, {"action": 1})
    assertNotContains(response, basic_event.name)
    assertContains(response, "Nothing needs action")
    assertContains(admin_client.get(url, {"action": 0}), basic_event.name)

    # Outstanding power test records bring it back, once
    models.PowerTestRecord.objects.create(event=basic_event, venue=venue)
    models.PowerTestRecord.objects.create(event=basic_event, venue=venue)
    assert admin_client.get(url, {"action": 1}).content.decode().count(basic_event.name) == 1


def test_hs_list_summary_counts(admin_client, admin_user, basic_event, ra):
    basic_event.status = models.Event.CONFIRMED
    basic_event.mic = admin_user
    basic_event.save()
    url = reverse("hs_list")

    response = admin_client.get(url)
    assert response.context["summary"] == {"red": 0, "amber": 1}

    # Reviewing the RA takes it out of the count
    review(admin_client, admin_user, ra, "ra_review")
    assert admin_client.get(url).context["summary"] == {"red": 0, "amber": 0}

    # Losing the MIC makes it red instead
    basic_event.mic = None
    basic_event.save()
    assert admin_client.get(url).context["summary"] == {"red": 1, "amber": 0}


@pytest.fixture
def dated_events(db, admin_user):
    """Confirmed events with no RA (so red): in 3 days, ended yesterday, ended 10 days ago, ended 30 days ago"""
    today = timezone.localdate()
    events = {}
    for key, days in (("future", 3), ("yesterday", -1), ("ten_days", -10), ("thirty_days", -30)):
        events[key] = models.Event.objects.create(
            name=f"dated {key}", start_date=today + timedelta(days=days), status=models.Event.CONFIRMED, mic=admin_user
        )
    return events


def names_on_page(response):
    return [event.name for event in response.context["object_list"]]


def test_hs_list_date_range(admin_client, dated_events):
    url = reverse("hs_list")
    upcoming = names_on_page(admin_client.get(url, {"range": "upcoming"}))
    assert upcoming == ["dated future"]
    recent = names_on_page(admin_client.get(url, {"range": "recent"}))
    assert set(recent) == {"dated future", "dated yesterday", "dated ten_days"}
    assert len(names_on_page(admin_client.get(url, {"range": "all"}))) == 4


def test_hs_list_order(admin_client, dated_events):
    url = reverse("hs_list")
    oldest = names_on_page(admin_client.get(url, {"range": "all", "order": "oldest"}))
    assert oldest == ["dated thirty_days", "dated ten_days", "dated yesterday", "dated future"]
    newest = names_on_page(admin_client.get(url, {"range": "all", "order": "newest"}))
    assert newest == list(reversed(oldest))


def test_hs_list_counts_follow_range(admin_client, dated_events):
    url = reverse("hs_list")
    assert admin_client.get(url, {"range": "upcoming"}).context["summary"] == {"red": 1, "amber": 0}
    assert admin_client.get(url, {"range": "recent"}).context["summary"] == {"red": 3, "amber": 0}
    assert admin_client.get(url, {"range": "all"}).context["summary"] == {"red": 4, "amber": 0}


def test_hs_list_options_are_remembered(admin_client, admin_user, dated_events):
    url = reverse("hs_list")
    admin_user.refresh_from_db()
    assert (admin_user.hs_order, admin_user.hs_range, admin_user.hs_only_action) == ("oldest", "upcoming", False)

    admin_client.get(url, {"range": "all", "order": "newest", "action": 1})
    admin_user.refresh_from_db()
    assert (admin_user.hs_order, admin_user.hs_range, admin_user.hs_only_action) == ("newest", "all", True)

    # A later visit with no options uses what was saved
    response = admin_client.get(url)
    assert response.context["date_range"] == "all"
    assert response.context["order"] == "newest"
    assert response.context["only_needing_action"] is True
    assert names_on_page(response)[0] == "dated future"

    # Rubbish values are ignored rather than saved
    admin_client.get(url, {"range": "nonsense", "order": "sideways", "action": 1})
    admin_user.refresh_from_db()
    assert (admin_user.hs_order, admin_user.hs_range) == ("newest", "all")


def test_hs_list_legacy_ignores_options(admin_client, admin_user, dated_events):
    admin_client.get(reverse("hs_list"), {"range": "upcoming", "order": "oldest", "action": 1})
    response = admin_client.get(reverse("hs_list"), {"legacy": 1})
    assert len(names_on_page(response)) == 4
    admin_user.refresh_from_db()
    assert (admin_user.hs_range, admin_user.hs_only_action) == ("upcoming", True)


def test_hs_list_legacy(admin_client, basic_event):
    response = admin_client.get(reverse("hs_list"), {"legacy": 1}, follow=True)
    assertContains(response, basic_event.name)
    assertContains(response, "Back to the new version")
    assertContains(response, "Power Records")


def test_hs_rag(basic_event, admin_user, ra):
    # Not confirmed: no RAG, whatever else is going on
    basic_event.status = models.Event.PROVISIONAL
    assert basic_event.hs_rag is None

    # Confirmed with an RA but no MIC: red
    basic_event.status = models.Event.CONFIRMED
    basic_event.mic = None
    assert basic_event.hs_rag == "red"
    assert basic_event.hs_rag_status[1] == "Confirmed event with no MIC assigned"

    # MIC and an unreviewed RA: amber
    basic_event.mic = admin_user
    assert basic_event.hs_rag == "amber"

    # MIC and a reviewed RA: green
    ra.reviewed_by = admin_user
    ra.save()
    basic_event.refresh_from_db()
    basic_event.status = models.Event.BOOKED
    basic_event.mic = admin_user
    assert basic_event.hs_rag == "green"


def test_hs_rag_outstanding_power_test(basic_event, admin_user, ra, power_test):
    basic_event.status = models.Event.CONFIRMED
    basic_event.mic = admin_user
    ra.reviewed_by = admin_user
    ra.save()
    basic_event.refresh_from_db()
    basic_event.status = models.Event.CONFIRMED
    basic_event.mic = admin_user

    # A reviewed RA is not enough while a power test record is outstanding
    assert basic_event.hs_rag == "amber"
    assert basic_event.hs_rag_status[1] == "Awaiting review: 1 power test record"

    power_test.reviewed_by = admin_user
    power_test.save()
    basic_event = models.Event.objects.get(pk=basic_event.pk)
    basic_event.status = models.Event.CONFIRMED
    basic_event.mic = admin_user
    assert basic_event.hs_rag == "green"


def test_hs_rag_no_ra(basic_event, admin_user):
    basic_event.status = models.Event.CONFIRMED
    basic_event.mic = admin_user
    assert basic_event.hs_rag == "red"
    assert basic_event.hs_rag_status[1] == "Confirmed event with no risk assessment"
    basic_event.mic = None
    assert basic_event.hs_rag_status[1] == "Confirmed event with no MIC assigned and no risk assessment"


def review(client, profile, obj, request_url):
    time = timezone.now()
    response = client.get(reverse(request_url, kwargs={"pk": obj.pk}), follow=True)
    obj.refresh_from_db()
    assertContains(response, "Reviewed by")
    assertContains(response, escape(profile.name))
    assert_times_almost_equal(time, obj.reviewed_at)


def test_ra_review(admin_client, admin_user, ra):
    review(admin_client, admin_user, ra, "ra_review")


def test_checklist_review(admin_client, admin_user, checklist):
    review(admin_client, admin_user, checklist, "ec_review")


def test_ra_redirect(admin_client, admin_user, ra):
    request_url = reverse("event_ra", kwargs={"pk": ra.event.pk})
    expected_url = reverse("ra_edit", kwargs={"pk": ra.pk})
    response = admin_client.get(request_url, follow=True)
    assertRedirects(response, expected_url, status_code=302, target_status_code=200)


class TestMarkdownTemplateTags(TestCase):
    with open(os.path.join(settings.BASE_DIR, "RIGS/tests/sample.md"), encoding="utf-8") as f:
        markdown = f.read()

    def test_html_safe(self):
        html = markdown_filter(self.markdown)
        self.assertIsInstance(html, SafeText)

    def test_img_strip(self):
        rml = markdown_filter(self.markdown, "rml")
        self.assertNotIn("<img", rml)

    def test_code(self):
        rml = markdown_filter(self.markdown, "rml")
        self.assertIn('<font face="Courier">monospace</font>', rml)

    def test_blockquote(self):
        rml = markdown_filter(self.markdown, "rml")
        self.assertIn("<pre>\nBlock quotes", rml)

    def test_lists(self):
        rml = markdown_filter(self.markdown, "rml")
        self.assertIn("<li><para>second item</para></li>", rml)  # <ol>
        self.assertIn("<li><para>that one</para></li>", rml)  # <ul>

    def test_in_print(self):
        event = models.Event.objects.create(
            name="MD Print Test",
            description=self.markdown,
            start_date="2016-01-01",
        )
        models.EventItem.objects.create(
            event=event, name="TI I1", quantity=1, cost=1.00, order=1, description="* test \n * test \n * test"
        )
        user = models.Profile.objects.create(
            username="RML test",
            is_superuser=True,  # Don't care about permissions
            is_active=True,
        )
        user.set_password("rmltester")
        user.save()

        self.assertTrue(self.client.login(username=user.username, password="rmltester"))
        response = self.client.get(reverse("event_print", kwargs={"pk": event.pk}))
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


def test_ra_big_power_without_power_mic_is_a_form_error(ra):
    data = model_to_dict(ra)
    data.update(big_power=True, power_mic=None, supervisor_consulted=True)
    form = forms.EventRiskAssessmentForm(data=data, instance=ra)
    assert not form.is_valid()
    assert form.errors["power_mic"].as_data()[0].code == "power_mic_required"


def test_checkin_person_picker_only_for_event_mic(client, admin_user, basic_event, django_user_model):
    other = django_user_model.objects.create_user(username="other", password="other", is_approved=True)
    basic_event.mic = admin_user
    basic_event.save()
    url = reverse("event_checkin", kwargs={"pk": basic_event.pk})

    client.force_login(admin_user)
    assertContains(client.get(url), "ts-select")

    client.force_login(other)
    assertNotContains(client.get(url), "ts-select")


def _invoiced_event(name, days_ago, cost, payments=(), status=models.Event.BOOKED):
    event = models.Event.objects.create(
        name=name, is_rig=True, status=status, start_date=date.today() - timedelta(days=days_ago)
    )
    models.EventItem.objects.create(event=event, name="Item", cost=cost, quantity=1, order=1)
    invoice = models.Invoice.objects.create(event=event)
    # Invoiced on the day of the event (the date is set automatically, so it's changed afterwards)
    models.Invoice.objects.filter(pk=invoice.pk).update(invoice_date=event.start_date)
    invoice.refresh_from_db()
    for paid_after, amount, method in payments:
        models.Payment.objects.create(
            invoice=invoice, date=invoice.invoice_date + timedelta(days=paid_after), amount=amount, method=method
        )
    return invoice


def test_invoice_dashboard_figures(admin_client):
    _invoiced_event("Paid", 10, 100, [(1, 100, models.Payment.EXTERNAL)])
    _invoiced_event("Part paid", 10, 50, [(2, 20, models.Payment.INTERNAL), (4, -5, models.Payment.ADJUSTMENT)])
    # A mistyped year shouldn't wreck the figure; legacy and retired methods still get names
    _invoiced_event("Typo", 10, 10, [(-730000, 10, "")])
    _invoiced_event("Legacy", 10, 10, [(3, 10, "SU")])
    _invoiced_event("Cancelled", 10, 0, status=models.Event.CANCELLED)
    models.Event.objects.create(name="Future", is_rig=True, start_date=date.today() + timedelta(days=10))
    voided = _invoiced_event("Voided", 10, 30)
    models.Invoice.objects.filter(pk=voided.pk).update(void=True)
    waiting = models.Event.objects.create(name="Waiting", is_rig=True, start_date=date.today() - timedelta(days=1))
    models.EventItem.objects.create(event=waiting, name="Item", cost=7, quantity=3, order=1)

    response = admin_client.get(reverse("invoice_dashboard"))
    context = response.context

    assert context["total_outstanding"] == 35
    assert context["outstanding_count"] == 1
    assert context["total_waiting"] == 21
    summary = context["summary"]
    assert summary["events"] == 6  # Not the cancelled or future events
    assert (summary["invoices"], summary["void_invoices"]) == (5, 1)
    assertContains(response, "Excludes 1 voided")
    assert summary["income"] == 140
    assert summary["adjustments"] == -5
    assert summary["median_days_to_pay"] == 2
    methods = [m["method"] for m in context["payment_methods"]]
    assert methods[:2] == ["External", "Internal"]
    assert set(methods[2:]) == {"Not recorded", "SU Core"}  # Adjustments aren't income
    assert [(stage["label"], stage["count"]) for stage in context["funnel"]] == [
        ("Events done", 6),
        ("Invoiced", 4),
        ("Paid in full", 3),
    ]
    checks = {check["title"]: check["count"] for check in context["data_quality"]}
    assert checks == {"Payments with impossible dates": 1, "Empty invoices for cancelled events": 1}
    # The impossible date is left out of the charts rather than stretching them over two thousand years
    assert len(context["charts"]["income"]["labels"]) == 1
    assertContains(response, 'id="finance-charts"')


def test_invoice_dashboard_aged_debt(admin_client):
    for days_ago, cost in [(10, 5), (60, 7), (200, 11), (400, 13), (800, 17)]:
        _invoiced_event(f"Owed {days_ago}", days_ago, cost)

    context = admin_client.get(reverse("invoice_dashboard")).context

    assert [(band["count"], band["total"]) for band in context["aged_debt"]] == [(1, 5), (1, 7), (1, 11), (2, 30)]
    checks = {check["title"]: check["count"] for check in context["data_quality"]}
    assert checks["Invoices owed for over a year"] == 2
    assert "Unusually large payments" not in {check["title"] for check in context["data_quality"]}


def test_invoice_dashboard_flags_large_payments(admin_client):
    _invoiced_event("Brian the Van", 10, 1000000, [(1, 1000000, "")])
    checks = {check["title"]: check for check in admin_client.get(reverse("invoice_dashboard")).context["data_quality"]}
    assert checks["Unusually large payments"]["count"] == 1


@pytest.mark.parametrize("time_filter", ["week", "month", "year", "all", "ay2020", "nonsense"])
def test_invoice_dashboard_periods(admin_client, time_filter):
    _invoiced_event("Paid", 3, 100, [(1, 100, models.Payment.EXTERNAL)])
    response = admin_client.get(reverse("invoice_dashboard"), {"time_filter": time_filter})
    assert response.status_code == 200
    assert response.context["period"].key == ("all" if time_filter == "nonsense" else time_filter)


def test_finance_periods():
    today = date(2026, 3, 1)
    year = finance_stats.get_period("ay2025", today)
    assert (year.start, year.end, year.label) == (date(2025, 9, 1), today, "Academic year 2025/26")
    # A year still under way is compared with the same point in the last one
    before = finance_stats.previous_period(year)
    assert (before.start, before.end, before.label) == (date(2024, 9, 1), date(2025, 3, 1), "the same point in 2024/25")
    finished = finance_stats.previous_period(finance_stats.get_period("ay2024", today))
    assert (finished.start, finished.end) == (date(2023, 9, 1), date(2024, 8, 31))

    week = finance_stats.get_period("week", today)
    previous_week = finance_stats.previous_period(week)
    assert previous_week.end == week.start - timedelta(days=1)
    assert previous_week.end - previous_week.start == week.end - week.start

    assert finance_stats.get_period("ay2030", today).key == "all"  # Hasn't started yet
    assert finance_stats.previous_period(finance_stats.get_period("all", today)) is None


def test_finance_deltas():
    current = {"income": 120, "median_days_to_pay": 5}
    previous = {"income": 100, "median_days_to_pay": 3}
    income = finance_stats.delta(current, previous, "income", "last year")
    assert (income["text"], income["tone"]) == ("20% up on last year", "success")
    # Taking longer to be paid is worse, though the number went up
    days = finance_stats.delta(current, previous, "median_days_to_pay", "last year", lower_is_better=True)
    assert (days["text"], days["tone"]) == ("2 days up on last year", "danger")
    assert finance_stats.delta(current, {"income": 0, "median_days_to_pay": None}, "income", "x") is None


def test_invoice_dashboard_export(admin_client):
    invoice = _invoiced_event("=HYPERLINK(1)", 10, 50, [(1, 20, models.Payment.INTERNAL)])

    response = admin_client.get(
        reverse("invoice_dashboard_export", kwargs={"kind": "invoices"}), {"time_filter": "year"}
    )
    assert response["Content-Type"] == "text/csv"
    rows = list(csv.reader(response.content.decode().splitlines()))
    assert rows[0][0] == "Invoice"
    assert rows[1][0] == invoice.display_id
    assert rows[1][3] == "'=HYPERLINK(1)"  # Not run as a formula when opened
    assert rows[1][7:10] == ["50.00", "20.00", "30.00"]

    response = admin_client.get(reverse("invoice_dashboard_export", kwargs={"kind": "payments"}))
    rows = list(csv.reader(response.content.decode().splitlines()))
    assert rows[1][6:] == ["Internal", "20.00"]

    assert admin_client.get(reverse("invoice_dashboard_export", kwargs={"kind": "people"})).status_code == 404


def test_invoice_dashboard_queries_dont_grow(admin_client):
    from django.core.cache import cache
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    def queries():
        cache.delete(models.INVOICE_COUNTS_CACHE_KEY)  # Every call pays for the navbar counts the same way
        with CaptureQueriesContext(connection) as captured:
            assert admin_client.get(reverse("invoice_dashboard")).status_code == 200
        return len(captured)

    for i in range(5):
        _invoiced_event(f"E{i}", i + 2, 100, [(1, 40, models.Payment.EXTERNAL)])
    queries()  # The first request also sets up the session and permissions
    few = queries()
    for i in range(30):
        _invoiced_event(f"F{i}", i * 30 + 2, 100, [(1, 40, models.Payment.EXTERNAL)])
    assert queries() == few


def _invoice_history(invoice):
    from reversion.models import Version

    return list(Version.objects.get_for_object(invoice).select_related("revision__user"))


def test_invoice_void_is_recorded(admin_client, admin_user):
    invoice = _invoiced_event("Voided", 10, 30)
    url = reverse("invoice_void", kwargs={"pk": invoice.pk})

    assert admin_client.get(url).status_code == 405
    invoice.refresh_from_db()
    assert not invoice.void

    assertRedirects(admin_client.post(url), reverse("invoice_list"))
    invoice.refresh_from_db()
    assert invoice.void
    latest = _invoice_history(invoice)[0]
    assert (latest.revision.user, latest.revision.comment) == (admin_user, "Invoice voided")
    assertContains(admin_client.get(reverse("activity_feed")), invoice.display_id)

    admin_client.post(url)
    invoice.refresh_from_db()
    assert not invoice.void
    assert _invoice_history(invoice)[0].revision.comment == "Invoice unvoided"


@pytest.mark.parametrize("url_name,void", [("invoice_event", False), ("invoice_event_void", True)])
def test_invoice_creation_is_recorded(admin_client, admin_user, url_name, void):
    event = models.Event.objects.create(name="To invoice", is_rig=True, start_date=date.today() - timedelta(days=2))
    url = reverse(url_name, kwargs={"pk": event.pk})

    assert admin_client.get(url).status_code == 405
    assert not models.Invoice.objects.filter(event=event).exists()

    response = admin_client.post(url)
    invoice = models.Invoice.objects.get(event=event)
    assertRedirects(response, reverse("invoice_detail", kwargs={"pk": invoice.pk}))
    assert invoice.void == void
    history = _invoice_history(invoice)
    assert len(history) == 1
    assert history[0].revision.user == admin_user
    assert history[0].revision.comment == ("Invoice created and voided" if void else "Invoice created")


def test_event_invoice_button(admin_client):
    event = models.Event.objects.create(name="To invoice", is_rig=True, start_date=date.today() - timedelta(days=2))
    url = reverse("event_detail", kwargs={"pk": event.pk})

    response = admin_client.get(url)
    assertContains(response, 'id="invoice-create-form"', count=1)
    assertContains(response, 'form="invoice-create-form"')

    invoice = models.Invoice.objects.create(event=event)
    response = admin_client.get(url)
    assertNotContains(response, "invoice-create-form")
    assertContains(response, reverse("invoice_detail", kwargs={"pk": invoice.pk}))


def test_normalise_initials():
    from RIGS.models import normalise_initials

    assert normalise_initials("ab") == "AB"
    assert normalise_initials("R.A.W") == "RAW"
    assert normalise_initials("D A W") == "DAW"
    assert normalise_initials("K_C") == "KC"
    assert normalise_initials("AD🎤") == "AD🎤"
    assert normalise_initials("ad 🎤") == "AD🎤"
    assert normalise_initials("AD🎤🎤") == "AD🎤"
    assert normalise_initials("") == ""
    assert normalise_initials(None) is None


def test_event_api_includes_display_id(admin_client):
    from RIGS import models

    event = models.Event.objects.create(name="Same Day", start_date=date(2030, 1, 1), is_rig=True)
    response = admin_client.get(
        reverse("api_secure", kwargs={"model": "event"}), {"start": "2030-01-01T00:00:00", "end": "2030-01-01T23:59:59"}
    )
    assert [e["display_id"] for e in response.json()] == [event.display_id]


def kanban_events():
    today = date.today()
    su = models.Organisation.objects.create(name="SU Society", union_account=True)
    external = models.Organisation.objects.create(name="External Ltd")
    return {
        "provisional": models.Event.objects.create(name="Future Prov", start_date=today + timedelta(days=5)),
        "booked": models.Event.objects.create(
            name="Future Booked", start_date=today + timedelta(days=5), status=models.Event.BOOKED, organisation=su
        ),
        "cancelled": models.Event.objects.create(
            name="Future Cancelled", start_date=today + timedelta(days=5), status=models.Event.CANCELLED
        ),
        "non_rig": models.Event.objects.create(name="Meeting", start_date=today + timedelta(days=5), is_rig=False),
        "awaiting": models.Event.objects.create(
            name="Just Finished", start_date=today - timedelta(days=3), organisation=external
        ),
        "old": models.Event.objects.create(name="Long Gone", start_date=today - timedelta(days=30)),
        "uni_org": models.Event.objects.create(
            name="Uni Dept",
            start_date=today + timedelta(days=6),
            status=models.Event.CONFIRMED,
            organisation=models.Organisation.objects.create(name="Physics", email="physics@Nottingham.ac.uk"),
        ),
        "uni_person": models.Event.objects.create(
            name="Uni Person",
            start_date=today + timedelta(days=7),
            status=models.Event.CONFIRMED,
            person=models.Person.objects.create(name="Lecturer", email="lecturer@nottingham.ac.uk"),
        ),
        "uni_internal": models.Event.objects.create(
            name="SU With Uni Email",
            start_date=today + timedelta(days=7),
            status=models.Event.CONFIRMED,
            organisation=models.Organisation.objects.create(
                name="SU Dept", email="su@nottingham.ac.uk", union_account=True
            ),
        ),
    }


def kanban_cell(response, lane, column):
    for row in response.context["lanes"]:
        if row["key"] == lane:
            return [event.name for cell in row["cells"] if cell["key"] == column for event in cell["events"]]


def test_kanban_columns_and_lanes(admin_client):
    events = kanban_events()
    invoiced = models.Event.objects.create(name="Invoiced", start_date=date.today() - timedelta(days=10))
    models.EventItem.objects.create(event=invoiced, name="Desk", cost=10, quantity=1, order=1)
    models.Invoice.objects.create(event=invoiced)
    paid = models.Event.objects.create(name="Paid", start_date=date.today() - timedelta(days=10))
    models.Invoice.objects.create(event=paid)
    void = models.Event.objects.create(name="Void", start_date=date.today() - timedelta(days=10))
    models.Invoice.objects.create(event=void, void=True)

    response = admin_client.get(reverse("event_kanban"))
    assert response.status_code == 200
    assert kanban_cell(response, "external", "provisional") == ["Future Prov"]
    assert kanban_cell(response, "internal", "booked") == ["Future Booked"]
    assert kanban_cell(response, "internal", "confirmed") == ["SU With Uni Email"]
    assert kanban_cell(response, "external", "booked") == []
    assert kanban_cell(response, "university", "confirmed") == ["Uni Dept", "Uni Person"]
    assert kanban_cell(response, "external", "awaiting_invoice") == ["Just Finished"]
    assert kanban_cell(response, "external", "invoiced") == ["Invoiced"]
    assert kanban_cell(response, "external", "paid") == ["Paid"]
    names = [event.name for lane in response.context["lanes"] for cell in lane["cells"] for event in cell["events"]]
    for gone in ("Future Cancelled", "Meeting", "Long Gone", "Void"):
        assert gone not in names
    assert kanban_older(response, "external", "awaiting_invoice") == 1
    assert events["old"].pk


def kanban_older(response, lane, column):
    for row in response.context["lanes"]:
        if row["key"] == lane:
            return next(cell["older"] for cell in row["cells"] if cell["key"] == column)


def test_kanban_only_paid_rigs_leave_unreported(admin_client):
    long_ago = date.today() - timedelta(days=60)
    su = models.Organisation.objects.create(name="SU Society", union_account=True)
    uni = models.Organisation.objects.create(name="Physics", email="physics@nottingham.ac.uk")

    def old_event(name, organisation=None, cost=0, paid=None, invoice=True, void=False, **kwargs):
        event = models.Event.objects.create(name=name, start_date=long_ago, organisation=organisation, **kwargs)
        if cost:
            models.EventItem.objects.create(event=event, name="Desk", cost=cost, quantity=1, order=1)
        if invoice:
            inv = models.Invoice.objects.create(event=event, void=void)
            if paid:
                models.Payment.objects.create(invoice=inv, date=long_ago, amount=paid)
        return event

    old_event("Not Invoiced", su, invoice=False)
    old_event("Owed", su, cost=100)
    old_event("Part Paid", uni, cost=100, paid=40)
    old_event("Paid", uni, cost=100, paid=100)
    old_event("Void", su, cost=100, void=True)
    old_event("Cancelled", su, invoice=False, status=models.Event.CANCELLED)

    response = admin_client.get(reverse("event_kanban"))
    names = [event.name for lane in response.context["lanes"] for cell in lane["cells"] for event in cell["events"]]
    assert names == []
    assert kanban_older(response, "internal", "awaiting_invoice") == 1
    assert kanban_older(response, "internal", "invoiced") == 1
    assert kanban_older(response, "university", "invoiced") == 1
    assert kanban_older(response, "university", "paid") == 0
    assertContains(response, "+1 older rig still owed on", count=2)
    assertContains(response, "+1 older rig not yet invoiced", count=1)
    assertNotContains(response, "leave the board")


def test_kanban_hides_finance_without_permission(client, django_user_model):
    kanban_events()
    user = django_user_model.objects.create_user(username="viewer", password="pw", is_approved=True)
    client.force_login(user)
    response = client.get(reverse("event_kanban"))
    assert [key for key, _ in response.context["columns"]] == ["provisional", "confirmed", "booked", "done"]
    assert kanban_cell(response, "external", "done") == ["Just Finished"]
    assertNotContains(response, 'data-dropzone="invoice"')
    assertNotContains(response, 'id="finance"')


def test_kanban_finance_preference(admin_client, admin_user):
    event = kanban_events()["awaiting"]
    invoiced = models.Event.objects.create(name="Invoiced", start_date=date.today() - timedelta(days=5))
    models.Invoice.objects.create(event=invoiced)
    url = reverse("event_kanban")

    response = admin_client.get(url)
    assert response.context["show_finance"] is True
    assertContains(response, 'data-dropzone="invoice"')

    response = admin_client.get(url, {"finance": "0"})
    admin_user.refresh_from_db()
    assert admin_user.kanban_finance is False
    assert [key for key, _ in response.context["columns"]][3:] == ["done"]
    assert sorted(kanban_cell(response, "external", "done")) == sorted(["Just Finished", "Invoiced"])
    assert event.name in kanban_cell(response, "external", "done")
    assert response.context["lanes"][0]["cells"][-1]["older"] == 0
    assertNotContains(response, 'data-dropzone="invoice"')
    assertNotContains(response, "older rig")

    # Remembered without being asked again, until it is switched back on
    assert [key for key, _ in admin_client.get(url).context["columns"]][3:] == ["done"]
    response = admin_client.get(url, {"finance": "1"})
    admin_user.refresh_from_db()
    assert admin_user.kanban_finance is True
    assert "done" not in [key for key, _ in response.context["columns"]]


def test_kanban_dry_hires_have_their_own_lane(admin_client):
    today = date.today()
    su = models.Organisation.objects.create(name="SU Society", union_account=True)
    models.Event.objects.create(
        name="SU Dry Hire", start_date=today + timedelta(days=3), organisation=su, dry_hire=True
    )
    models.Event.objects.create(name="Plain Dry Hire", start_date=today + timedelta(days=4), dry_hire=True)
    models.Event.objects.create(name="SU Rig", start_date=today + timedelta(days=3), organisation=su)

    response = admin_client.get(reverse("event_kanban"))
    assert [lane["key"] for lane in response.context["lanes"]][-1] == "dry_hire"
    assert kanban_cell(response, "dry_hire", "provisional") == ["SU Dry Hire", "Plain Dry Hire"]
    assert kanban_cell(response, "internal", "provisional") == ["SU Rig"]


def test_kanban_invoice_before_the_event_keeps_its_column(admin_client):
    today = date.today()
    event = models.Event.objects.create(
        name="Invoiced Early", start_date=today + timedelta(days=5), status=models.Event.BOOKED
    )
    models.EventItem.objects.create(event=event, name="Desk", cost=10, quantity=1, order=1)
    models.Invoice.objects.create(event=event)
    voided = models.Event.objects.create(name="Voided Early", start_date=today + timedelta(days=5))
    models.Invoice.objects.create(event=voided, void=True)

    response = admin_client.get(reverse("event_kanban"))
    assert kanban_cell(response, "external", "booked") == ["Invoiced Early"]
    assert kanban_cell(response, "external", "provisional") == ["Voided Early"]
    assertContains(response, "Invoiced #")
    assertContains(response, "data-invoiced", count=1)

    # It can still change status, but can't be cancelled while the invoice stands
    url = reverse("event_kanban_status", kwargs={"pk": event.pk})
    response = admin_client.post(url, {"status": models.Event.CONFIRMED})
    assert response.status_code == 200
    assert response.json()["column"] == "confirmed"
    assert admin_client.post(url, {"status": models.Event.CANCELLED}).status_code == 409
    event.refresh_from_db()
    assert event.status == models.Event.CONFIRMED

    # Once it has happened it moves on with the rest
    event.start_date = today - timedelta(days=1)
    event.save()
    response = admin_client.get(reverse("event_kanban"))
    assert kanban_cell(response, "external", "invoiced") == ["Invoiced Early"]


def test_kanban_invoice_ahead_of_the_event(admin_client):
    event = models.Event.objects.create(name="Early", start_date=date.today() + timedelta(days=5))
    response = admin_client.post(reverse("event_kanban_invoice", kwargs={"pk": event.pk}))
    assert response.json()["created"] is True
    assert response.json()["column"] == "provisional"


def test_kanban_invoice_refused_when_voided(admin_client):
    event = models.Event.objects.create(name="Voided", start_date=date.today() + timedelta(days=5))
    models.Invoice.objects.create(event=event, void=True)
    response = admin_client.post(reverse("event_kanban_invoice", kwargs={"pk": event.pk}))
    assert response.status_code == 409


def kanban_flags(**kwargs):
    from RIGS.views.kanban import flags_for

    defaults = {
        "name": "Flag Test",
        "start_date": date.today() + timedelta(days=5),
        "start_time": time(18, 0),
        "venue": models.Venue.objects.get_or_create(name="Venue")[0],
        "organisation": models.Organisation.objects.get_or_create(name="Client")[0],
        "mic": models.Profile.objects.get_or_create(username="mic", initials="MIC")[0],
        "forum_url": "https://forum.nottinghamtec.co.uk/t/1",
        "default_response_sent": True,
    }
    event = models.Event.objects.create(**{**defaults, **kwargs})
    return [flag["key"] for flag in flags_for(event, date.today())]


def test_kanban_flags():
    assert kanban_flags() == []
    assert kanban_flags(default_response_sent=False) == ["default_response"]
    assert kanban_flags(default_response_sent=False, status=models.Event.CONFIRMED) == []
    assert kanban_flags(venue=None) == ["details"]
    assert kanban_flags(organisation=None) == ["details"]
    assert kanban_flags(start_time=None) == ["details"]
    assert kanban_flags(mic=None) == ["mic"]
    assert kanban_flags(mic=None, status=models.Event.BOOKED) == ["mic"]
    assert kanban_flags(forum_url="") == []
    assert kanban_flags(forum_url="", status=models.Event.CONFIRMED) == ["forum"]
    assert kanban_flags(forum_url="", status=models.Event.BOOKED) == ["forum"]


def test_kanban_flags_for_dry_hires():
    assert kanban_flags(dry_hire=True, venue=None, mic=None, forum_url="", status=models.Event.BOOKED) == []
    assert kanban_flags(dry_hire=True, default_response_sent=False) == ["default_response"]
    assert kanban_flags(dry_hire=True, organisation=None) == ["details"]


def test_kanban_flags_only_for_upcoming_events():
    today = date.today()
    assert kanban_flags(start_date=today - timedelta(days=3), default_response_sent=False, mic=None) == []
    assert kanban_flags(status=models.Event.CANCELLED, default_response_sent=False, mic=None) == []


def test_kanban_flags_on_the_page_and_in_responses(admin_client):
    event = models.Event.objects.create(name="Needs Chasing", start_date=date.today() + timedelta(days=5))
    response = admin_client.get(reverse("event_kanban"))
    for flag in ("default_response", "details", "mic"):
        assertContains(response, f'data-flag="{flag}"')
    assertContains(response, "kanban-card-flagged")
    assertContains(response, "Basic details are missing: venue, client, start time")

    response = admin_client.post(
        reverse("event_kanban_status", kwargs={"pk": event.pk}), {"status": models.Event.CONFIRMED}
    )
    assert [flag["key"] for flag in response.json()["flags"]] == ["details", "forum", "mic"]


def test_event_duplicate_needs_a_new_default_response(admin_client):
    event = models.Event.objects.create(name="Original", start_date=date.today(), default_response_sent=True)
    response = admin_client.get(reverse("event_duplicate", kwargs={"pk": event.pk}))
    assert response.context["object"].default_response_sent is False
    event.refresh_from_db()
    assert event.default_response_sent is True


def test_kanban_default_response_migration_leaves_only_current_provisionals_flagged():
    from importlib import import_module

    from django.apps import apps

    migration = import_module("RIGS.migrations.0059_kanban_fields")
    today = date.today()
    current = models.Event.objects.create(name="Current", start_date=today + timedelta(days=5))
    past = models.Event.objects.create(name="Past", start_date=today - timedelta(days=5))
    booked = models.Event.objects.create(
        name="Booked", start_date=today + timedelta(days=5), status=models.Event.BOOKED
    )
    migration.mark_existing_responses_sent(apps, None)
    flags = dict(models.Event.objects.values_list("name", "default_response_sent"))
    assert flags == {"Current": False, "Past": True, "Booked": True}
    assert current.pk and past.pk and booked.pk


def test_kanban_status_change(admin_client):
    event = kanban_events()["provisional"]
    url = reverse("event_kanban_status", kwargs={"pk": event.pk})
    response = admin_client.post(url, {"status": models.Event.BOOKED})
    assert response.status_code == 200
    assert response.json()["column"] == "booked"
    assert response.json()["previous_status"] == models.Event.PROVISIONAL
    event.refresh_from_db()
    assert event.status == models.Event.BOOKED

    response = admin_client.post(url, {"status": models.Event.CANCELLED})
    event.refresh_from_db()
    assert event.status == models.Event.CANCELLED

    assert admin_client.post(url, {"status": 99}).status_code == 400
    assert admin_client.post(url, {"status": "x"}).status_code == 400


def test_kanban_status_change_refused_once_invoiced(admin_client):
    event = kanban_events()["awaiting"]
    models.Invoice.objects.create(event=event)
    response = admin_client.post(
        reverse("event_kanban_status", kwargs={"pk": event.pk}), {"status": models.Event.CANCELLED}
    )
    assert response.status_code == 409
    event.refresh_from_db()
    assert event.status == models.Event.PROVISIONAL


def test_kanban_invoice(admin_client):
    event = kanban_events()["awaiting"]
    models.EventItem.objects.create(event=event, name="Desk", cost=10, quantity=1, order=1)
    url = reverse("event_kanban_invoice", kwargs={"pk": event.pk})
    response = admin_client.post(url)
    assert response.status_code == 200
    data = response.json()
    invoice = models.Invoice.objects.get(event=event)
    assert data["created"] is True
    assert data["column"] == "invoiced"
    assert data["invoice"]["url"] == reverse("invoice_detail", kwargs={"pk": invoice.pk})

    response = admin_client.post(url)
    assert response.json()["created"] is False
    assert models.Invoice.objects.filter(event=event).count() == 1


def test_kanban_invoice_refused_when_cancelled(admin_client):
    event = kanban_events()["cancelled"]
    response = admin_client.post(reverse("event_kanban_invoice", kwargs={"pk": event.pk}))
    assert response.status_code == 409
    assert not models.Invoice.objects.filter(event=event).exists()


def test_kanban_actions_need_permission(client, django_user_model):
    event = kanban_events()["provisional"]
    user = django_user_model.objects.create_user(username="viewer", password="pw", is_approved=True)
    client.force_login(user)
    response = client.post(reverse("event_kanban_status", kwargs={"pk": event.pk}), {"status": models.Event.BOOKED})
    assert response.status_code == 403
    response = client.post(reverse("event_kanban_invoice", kwargs={"pk": event.pk}))
    assert response.status_code == 403
    event.refresh_from_db()
    assert event.status == models.Event.PROVISIONAL


def test_kanban_horizon(admin_client):
    today = date.today()
    soon = models.Event.objects.create(name="Soon", start_date=today + timedelta(days=10))
    later = models.Event.objects.create(name="In Four Months", start_date=today + timedelta(days=120))
    models.Event.objects.create(name="In Two Years", start_date=today + timedelta(days=730))

    def shown(**params):
        response = admin_client.get(reverse("event_kanban"), params)
        return response, kanban_cell(response, "external", "provisional")

    response, names = shown()
    assert response.context["horizon"] == "6m"
    assert names == [soon.name, later.name]
    assert response.context["beyond_horizon"] == 1

    assert shown(horizon="1m")[1] == [soon.name]
    assert shown(horizon="all")[1] == [soon.name, later.name, "In Two Years"]
    assert "beyond_horizon" not in shown(horizon="all")[0].context
    assert shown(horizon="nonsense")[0].context["horizon"] == "6m"


def test_months_after():
    from RIGS.views.kanban import months_after

    assert months_after(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert months_after(date(2026, 11, 15), 3) == date(2027, 2, 15)
    assert months_after(date(2026, 6, 1), 12) == date(2027, 6, 1)


def test_kanban_mark_response_sent(admin_client):
    event = models.Event.objects.create(name="Awaiting Reply", start_date=date.today() + timedelta(days=5))
    url = reverse("event_kanban_response", kwargs={"pk": event.pk})
    page = admin_client.get(reverse("event_kanban"))
    assertContains(page, 'data-kanban-action="response"')

    response = admin_client.post(url)
    assert response.status_code == 200
    assert "default_response" not in [flag["key"] for flag in response.json()["flags"]]
    event.refresh_from_db()
    assert event.default_response_sent is True

    response = admin_client.post(url, {"sent": "0"})
    assert "default_response" in [flag["key"] for flag in response.json()["flags"]]
    event.refresh_from_db()
    assert event.default_response_sent is False


def test_kanban_mark_response_sent_needs_permission(client, django_user_model):
    event = models.Event.objects.create(name="Awaiting Reply", start_date=date.today() + timedelta(days=5))
    user = django_user_model.objects.create_user(username="viewer", password="pw", is_approved=True)
    client.force_login(user)
    assert client.post(reverse("event_kanban_response", kwargs={"pk": event.pk})).status_code == 403
    page = client.get(reverse("event_kanban"))
    assertContains(page, 'data-flag="default_response"')
    assertNotContains(page, 'data-kanban-action="response"')
    event.refresh_from_db()
    assert event.default_response_sent is False


def test_kanban_missing_mic_is_urgent(admin_client):
    event = models.Event.objects.create(name="No MIC", start_date=date.today() + timedelta(days=5))
    response = admin_client.get(reverse("event_kanban"))
    assert 'class="card kanban-card shadow-sm kanban-card-urgent"' in response.content.decode()
    assert "No MIC" in response.content.decode()
    event.mic = models.Profile.objects.create(username="mic", initials="MIC")
    event.save()
    response = admin_client.get(reverse("event_kanban"))
    assert "kanban-card-urgent" not in response.content.decode().split('id="kanban"')[1]


def test_needing_mic_only_lists_upcoming_rigs_that_need_one():
    today = date.today()
    mic = models.Profile.objects.create(username="mic", initials="MIC")
    wanted = models.Event.objects.create(name="Wanted", start_date=today + timedelta(days=2))
    models.Event.objects.create(name="Has MIC", start_date=today + timedelta(days=2), mic=mic)
    models.Event.objects.create(name="Dry", start_date=today + timedelta(days=2), dry_hire=True)
    models.Event.objects.create(name="Cancelled", start_date=today + timedelta(days=2), status=models.Event.CANCELLED)
    models.Event.objects.create(name="Past", start_date=today - timedelta(days=2))
    models.Event.objects.create(name="Meeting", start_date=today + timedelta(days=2), is_rig=False)
    assert list(models.Event.objects.needing_mic()) == [wanted]


def test_home_page_adopt_a_rig(admin_client):
    event = models.Event.objects.create(name="Orphan", start_date=date.today() + timedelta(days=2))
    response = admin_client.get(reverse("index"))
    assert "Adopt a rig" in response.content.decode()
    assert reverse("event_adopt", kwargs={"pk": event.pk}) in response.content.decode()
    event.mic = models.Profile.objects.create(username="mic", initials="MIC")
    event.save()
    assert "Adopt a rig" not in admin_client.get(reverse("index")).content.decode()


def test_adopt_a_rig_makes_you_the_mic(admin_client, admin_user):
    event = models.Event.objects.create(name="Orphan", start_date=date.today() + timedelta(days=2))
    response = admin_client.post(reverse("event_adopt", kwargs={"pk": event.pk}))
    assert response.status_code == 302
    event.refresh_from_db()
    assert event.mic == admin_user


def test_adopt_a_rig_does_not_steal_someone_elses(admin_client):
    other = models.Profile.objects.create(username="other", initials="OTH")
    event = models.Event.objects.create(name="Taken", start_date=date.today() + timedelta(days=2), mic=other)
    admin_client.post(reverse("event_adopt", kwargs={"pk": event.pk}))
    event.refresh_from_db()
    assert event.mic == other


def test_adopt_a_rig_needs_permission(client, django_user_model):
    client.force_login(django_user_model.objects.create(username="viewer"))
    event = models.Event.objects.create(name="Orphan", start_date=date.today() + timedelta(days=2))
    assert client.post(reverse("event_adopt", kwargs={"pk": event.pk})).status_code == 403
    assert models.Event.objects.get(pk=event.pk).mic is None


def test_sharepoint_url_must_be_on_sharepoint(admin_client):
    event = models.Event.objects.create(name="Linked", start_date=date.today())
    event.sharepoint_url = "https://example.com/folder"
    with pytest.raises(ValidationError):
        event.full_clean()
    event.sharepoint_url = "https://nottinghamtec.sharepoint.com/:f:/s/Office/abc?e=def"
    event.full_clean()


def test_sharepoint_button_only_when_set(admin_client):
    event = models.Event.objects.create(name="Linked", start_date=date.today())
    url = reverse("event_detail", kwargs={"pk": event.pk})
    assert "Go to SharePoint" not in admin_client.get(url).content.decode()
    event.sharepoint_url = "https://nottinghamtec.sharepoint.com/:f:/s/Office/abc"
    event.save()
    content = admin_client.get(url).content.decode()
    assert content.count('class="btn btn-sharepoint"') >= 2


def test_event_duplicate_drops_the_sharepoint_link(admin_client):
    event = models.Event.objects.create(
        name="Original", start_date=date.today(), sharepoint_url="https://nottinghamtec.sharepoint.com/:f:/s/Office/abc"
    )
    response = admin_client.get(reverse("event_duplicate", kwargs={"pk": event.pk}))
    assert response.context["object"].sharepoint_url == ""

import csv
import os
import pytest
from datetime import date, timedelta

from django.conf import settings
from django.utils.html import escape
from django.core.exceptions import ObjectDoesNotExist
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

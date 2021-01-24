from datetime import date

from django.core.exceptions import ObjectDoesNotExist
from django.core.management import call_command
from django.urls import reverse
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import timezone

from RIGS import models
from reversion import revisions as reversion


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
        response = self.client.post(request_url, follow=True)

        # Check the invoice is deleted
        self.assertRaises(ObjectDoesNotExist, models.Invoice.objects.get, pk=self.invoices[2].pk)

    def test_invoice_delete_not_allowed(self):
        request_url = reverse('invoice_delete', kwargs={'pk': self.invoices[1].pk})

        response = self.client.get(request_url, follow=True)
        self.assertContains(response, "To delete an invoice, delete the payments first.")

        # Check the invoice still exists
        self.assertTrue(models.Invoice.objects.get(pk=self.invoices[1].pk))

        # Try to actually delete it
        response = self.client.post(request_url, follow=True)

        # Check this didn't work
        self.assertTrue(models.Invoice.objects.get(pk=self.invoices[1].pk))


class TestPrintPaperwork(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.profile = models.Profile.objects.create(username="testuser1", email="1@test.com", is_superuser=True,
                                                    is_active=True, is_staff=True)

        cls.vatrate = models.VatRate.objects.create(start_at='2014-03-05', rate=0.20, comment='test1')

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


class TestEmbeddedViews(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.profile = models.Profile.objects.create(username="testuser1", email="1@test.com", is_superuser=True,
                                                    is_active=True, is_staff=True)

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

    def testLoginRedirect(self):
        request_url = reverse('event_embed', kwargs={'pk': 1})
        expected_url = "{0}?next={1}".format(reverse('login_embed'), request_url)

        # Request the page and check it redirects
        response = self.client.get(request_url, follow=True)
        self.assertRedirects(response, expected_url, status_code=302, target_status_code=200)

        # Now login
        self.assertTrue(self.client.login(username=self.profile.username, password='testuser'))

        # And check that it no longer redirects
        response = self.client.get(request_url, follow=True)
        self.assertEqual(len(response.redirect_chain), 0)

    def testLoginCookieWarning(self):
        login_url = reverse('login_embed')
        response = self.client.post(login_url, follow=True)
        self.assertContains(response, "Cookies do not seem to be enabled")

    def testXFrameHeaders(self):
        event_url = reverse('event_embed', kwargs={'pk': 1})
        login_url = reverse('login_embed')

        self.assertTrue(self.client.login(username=self.profile.username, password='testuser'))

        response = self.client.get(event_url, follow=True)
        with self.assertRaises(KeyError):
            response._headers["X-Frame-Options"]

        response = self.client.get(login_url, follow=True)
        with self.assertRaises(KeyError):
            response._headers["X-Frame-Options"]

    def testOEmbed(self):
        event_url = reverse('event_detail', kwargs={'pk': 1})
        event_embed_url = reverse('event_embed', kwargs={'pk': 1})
        oembed_url = reverse('event_oembed', kwargs={'pk': 1})

        alt_oembed_url = reverse('event_oembed', kwargs={'pk': 999})
        alt_event_embed_url = reverse('event_embed', kwargs={'pk': 999})

        # Test the meta tag is in place
        response = self.client.get(event_url, follow=True, HTTP_HOST='example.com')
        self.assertContains(response, '<link rel="alternate" type="application/json+oembed"')
        self.assertContains(response, oembed_url)

        # Test that the JSON exists
        response = self.client.get(oembed_url, follow=True, HTTP_HOST='example.com')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, event_embed_url)

        # Should also work for non-existant events
        response = self.client.get(alt_oembed_url, follow=True, HTTP_HOST='example.com')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, alt_event_embed_url)


class TestSampleDataGenerator(TestCase):
    @override_settings(DEBUG=True)
    def test_generate_sample_data(self):
        # Run the management command and check there are no exceptions
        call_command('generateSampleRIGSData')

        # Check there are lots of events
        self.assertTrue(models.Event.objects.all().count() > 100)

    def test_production_exception(self):
        from django.core.management.base import CommandError

        self.assertRaisesRegex(CommandError, ".*production", call_command, 'generateSampleRIGSData')


class TestSearchLogic(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.profile = models.Profile.objects.create(username="testuser1", email="1@test.com", is_superuser=True,
                                                    is_active=True, is_staff=True)

        cls.persons = {
            1: models.Person.objects.create(name="Right Person", phone="1234"),
            2: models.Person.objects.create(name="Wrong Person", phone="5678"),
        }

        cls.organisations = {
            1: models.Organisation.objects.create(name="Right Organisation", email="test@example.com"),
            2: models.Organisation.objects.create(name="Wrong Organisation", email="check@fake.co.uk"),
        }

        cls.venues = {
            1: models.Venue.objects.create(name="Right Venue", address="1 Test Street, EX1"),
            2: models.Venue.objects.create(name="Wrong Venue", address="2 Check Way, TS2"),
        }

        cls.events = {
            1: models.Event.objects.create(name="Right Event", start_date=date.today(), person=cls.persons[1],
                                           organisation=cls.organisations[1], venue=cls.venues[1]),
            2: models.Event.objects.create(name="Wrong Event", start_date=date.today(), person=cls.persons[2],
                                           organisation=cls.organisations[2], venue=cls.venues[2]),
        }

    def setUp(self):
        self.profile.set_password('testuser')
        self.profile.save()
        self.assertTrue(self.client.login(username=self.profile.username, password='testuser'))

    def test_event_search(self):
        # Test search by name
        request_url = "%s?q=%s" % (reverse('event_archive'), self.events[1].name)
        response = self.client.get(request_url, follow=True)
        self.assertContains(response, self.events[1].name)
        self.assertNotContains(response, self.events[2].name)

        # Test search by ID
        request_url = "%s?q=%s" % (reverse('event_archive'), self.events[1].pk)
        response = self.client.get(request_url, follow=True)
        self.assertContains(response, self.events[1].name)
        self.assertNotContains(response, self.events[2].name)

    def test_people_search(self):
        # Test search by name
        request_url = "%s?q=%s" % (reverse('person_list'), self.persons[1].name)
        response = self.client.get(request_url, follow=True)
        self.assertContains(response, self.persons[1].name)
        self.assertNotContains(response, self.persons[2].name)

        # Test search by ID
        request_url = "%s?q=%s" % (reverse('person_list'), self.persons[1].pk)
        response = self.client.get(request_url, follow=True)
        self.assertContains(response, self.persons[1].name)
        self.assertNotContains(response, self.persons[2].name)

        # Test search by phone
        request_url = "%s?q=%s" % (reverse('person_list'), self.persons[1].phone)
        response = self.client.get(request_url, follow=True)
        self.assertContains(response, self.persons[1].name)
        self.assertNotContains(response, self.persons[2].name)

    def test_organisation_search(self):
        # Test search by name
        request_url = "%s?q=%s" % (reverse('organisation_list'), self.organisations[1].name)
        response = self.client.get(request_url, follow=True)
        self.assertContains(response, self.organisations[1].name)
        self.assertNotContains(response, self.organisations[2].name)

        # Test search by ID
        request_url = "%s?q=%s" % (reverse('organisation_list'), self.organisations[1].pk)
        response = self.client.get(request_url, follow=True)
        self.assertContains(response, self.organisations[1].name)
        self.assertNotContains(response, self.organisations[2].name)

        # Test search by email
        request_url = "%s?q=%s" % (reverse('organisation_list'), self.organisations[1].email)
        response = self.client.get(request_url, follow=True)
        self.assertContains(response, self.organisations[1].email)
        self.assertNotContains(response, self.organisations[2].email)

    def test_venue_search(self):
        # Test search by name
        request_url = "%s?q=%s" % (reverse('venue_list'), self.venues[1].name)
        response = self.client.get(request_url, follow=True)
        self.assertContains(response, self.venues[1].name)
        self.assertNotContains(response, self.venues[2].name)

        # Test search by ID
        request_url = "%s?q=%s" % (reverse('venue_list'), self.venues[1].pk)
        response = self.client.get(request_url, follow=True)
        self.assertContains(response, self.venues[1].name)
        self.assertNotContains(response, self.venues[2].name)

        # Test search by address
        request_url = "%s?q=%s" % (reverse('venue_list'), self.venues[1].address)
        response = self.client.get(request_url, follow=True)
        self.assertContains(response, self.venues[1].address)
        self.assertNotContains(response, self.venues[2].address)


class TestHSLogic(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.profile = models.Profile.objects.create(username="testuser1", email="1@test.com", is_superuser=True,
                                                    is_active=True, is_staff=True)

        cls.vatrate = models.VatRate.objects.create(start_at='2014-03-05', rate=0.20, comment='test1')
        cls.venue = models.Venue.objects.create(name="Venue 1")

        cls.events = {
            1: models.Event.objects.create(name="TE E1", start_date=date.today(),
                                           description="This is an event description\nthat for a very specific reason spans two lines.",
                                           venue=cls.venue),
            2: models.Event.objects.create(name="TE E2", start_date=date.today()),
        }

        cls.ras = {
            1: models.RiskAssessment.objects.create(event=cls.events[1],
                                                    nonstandard_equipment=False,
                                                    nonstandard_use=False,
                                                    contractors=False,
                                                    other_companies=False,
                                                    crew_fatigue=False,
                                                    big_power=False,
                                                    power_mic=cls.profile,
                                                    generators=False,
                                                    other_companies_power=False,
                                                    nonstandard_equipment_power=False,
                                                    multiple_electrical_environments=False,
                                                    noise_monitoring=False,
                                                    known_venue=True,
                                                    safe_loading=True,
                                                    safe_storage=True,
                                                    area_outside_of_control=True,
                                                    barrier_required=True,
                                                    nonstandard_emergency_procedure=True,
                                                    special_structures=False,
                                                    suspended_structures=False,
                                                    outside=False),
        }

        cls.checklists = {
            1: models.EventChecklist.objects.create(event=cls.events[1],
                                                    power_mic=cls.profile,
                                                    safe_parking=False,
                                                    safe_packing=False,
                                                    exits=False,
                                                    trip_hazard=False,
                                                    warning_signs=False,
                                                    ear_plugs=False,
                                                    hs_location="Locked away safely",
                                                    extinguishers_location="Somewhere, I forgot",
                                                    earthing=False,
                                                    pat=False,
                                                    date=timezone.now(),
                                                    venue=cls.venue),
        }

    def setUp(self):
        self.profile.set_password('testuser')
        self.profile.save()
        self.assertTrue(self.client.login(username=self.profile.username, password='testuser'))

    def test_list(self):
        request_url = reverse('hs_list')
        response = self.client.get(request_url, follow=True)
        self.assertContains(response, self.events[1].name)
        self.assertContains(response, self.events[2].name)
        self.assertContains(response, 'Create')

    def test_ra_review(self):
        request_url = reverse('ra_review', kwargs={'pk': self.ras[1].pk})
        response = self.client.get(request_url, follow=True)
        self.assertContains(response, 'Reviewed by')
        self.assertContains(response, self.profile.name)
        ra = models.RiskAssessment.objects.get(event=self.events[1])
        self.assertEqual(timezone.now().date(), ra.reviewed_at.date())
        self.assertEqual(timezone.now().hour, ra.reviewed_at.hour)
        self.assertEqual(timezone.now().minute, ra.reviewed_at.minute)

    def test_checklist_review(self):
        request_url = reverse('ec_review', kwargs={'pk': self.checklists[1].pk})
        response = self.client.get(request_url, follow=True)
        self.assertContains(response, 'Reviewed by')
        self.assertContains(response, self.profile.name)
        checklist = models.EventChecklist.objects.get(event=self.events[1])
        self.assertEqual(timezone.now().date(), checklist.reviewed_at.date())
        self.assertEqual(timezone.now().hour, checklist.reviewed_at.hour)
        self.assertEqual(timezone.now().minute, checklist.reviewed_at.minute)

    def test_ra_redirect(self):
        request_url = reverse('event_ra', kwargs={'pk': self.events[1].pk})
        expected_url = reverse('ra_edit', kwargs={'pk': self.ras[1].pk})

        response = self.client.get(request_url, follow=True)
        self.assertRedirects(response, expected_url, status_code=302, target_status_code=200)

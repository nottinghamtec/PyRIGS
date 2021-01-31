from datetime import date

from django.test import TestCase
from django.urls import reverse
from reversion import revisions as reversion

from RIGS import models
from assets import models as amodels
from versioning import versioning


# Model Tests
class RIGSVersionTestCase(TestCase):
    def setUp(self):
        models.VatRate.objects.create(rate=0.20, comment="TP V1", start_at='2013-01-01')

        self.profile = models.Profile.objects.get_or_create(
            first_name='Test',
            last_name='TEC User',
            username='eventauthtest',
            email='teccie@functional.test',
            is_superuser=True  # lazily grant all permissions
        )[0]
        with reversion.create_revision():
            reversion.set_user(self.profile)
            self.person = models.Person.objects.create(name='Authorisation Test Person')

        with reversion.create_revision():
            reversion.set_user(self.profile)
            self.organisation = models.Organisation.objects.create(name='Authorisation Test Organisation')

        with reversion.create_revision():
            reversion.set_user(self.profile)
            self.event = models.Event.objects.create(name="AuthorisationTestCase", person=self.person,
                                                     start_date=date.today())

        with reversion.create_revision():
            reversion.set_user(self.profile)
            self.event.notes = "A new note on the event"
            self.event.save()

    def test_find_parent_version(self):
        # Find the most recent version
        currentVersion = versioning.RIGSVersion.objects.get_for_object(self.event).latest('revision__date_created')
        self.assertEqual(currentVersion._object_version.object.notes, "A new note on the event")

        # Check the prev version is loaded correctly
        previousVersion = currentVersion.parent
        self.assertEqual(previousVersion._object_version.object.notes, None)

        # Check that finding the parent of the first version fails gracefully
        self.assertFalse(previousVersion.parent)

    def test_changes_since(self):
        # Find the most recent version
        currentVersion = versioning.RIGSVersion.objects.get_for_object(self.event).latest('revision__date_created')

        changes = currentVersion.changes
        self.assertEqual(len(changes.field_changes), 1)

    def test_manager(self):
        objs = versioning.RIGSVersion.objects.get_for_multiple_models(
            [models.Event, models.Person, models.Organisation])
        self.assertEqual(len(objs), 4)

    def test_text_field_types(self):
        with reversion.create_revision():
            reversion.set_user(self.profile)
            self.event.name = "New event name"  # Simple text
            self.event.description = "hello world"  # Long text
            self.event.save()

        # Find the most recent version
        currentVersion = versioning.RIGSVersion.objects.get_for_object(self.event).latest('revision__date_created')
        diff = currentVersion.changes

        # There are two changes
        self.assertEqual(len(diff.field_changes), 2)
        self.assertFalse(currentVersion.changes.items_changed)
        self.assertTrue(currentVersion.changes.fields_changed)
        self.assertTrue(currentVersion.changes.anything_changed)

        # Only one has "linebreaks"
        self.assertEqual(sum([x.linebreaks for x in diff.field_changes]), 1)

        # None are "long" (email address)
        self.assertEqual(sum([x.long for x in diff.field_changes]), 0)

        # Try changing email field in person
        with reversion.create_revision():
            reversion.set_user(self.profile)
            self.person.email = "hello@world.com"
            self.person.save()

        # Find the most recent version
        currentVersion = versioning.RIGSVersion.objects.get_for_object(self.person).latest('revision__date_created')
        diff = currentVersion.changes

        # Should be declared as long
        self.assertTrue(diff.field_changes[0].long)

    def test_text_diff(self):
        with reversion.create_revision():
            reversion.set_user(self.profile)
            self.event.notes = "An old note on the event"  # Simple text
            self.event.save()

        # Find the most recent version
        currentVersion = versioning.RIGSVersion.objects.get_for_object(self.event).latest('revision__date_created')

        # Check the diff is correct
        self.assertEqual(currentVersion.changes.field_changes[0].diff,
                         [{'type': 'equal', 'text': "A"},
                          {'type': 'delete', 'text': " new"},
                          {'type': 'insert', 'text': "n old"},
                          {'type': 'equal', 'text': " note on the event"}
                          ])

    def test_choice_field(self):
        with reversion.create_revision():
            reversion.set_user(self.profile)
            self.event.status = models.Event.CONFIRMED
            self.event.save()

        currentVersion = versioning.RIGSVersion.objects.get_for_object(self.event).latest('revision__date_created')
        self.assertEqual(currentVersion.changes.field_changes[0].old, 'Provisional')
        self.assertEqual(currentVersion.changes.field_changes[0].new, 'Confirmed')

    def test_creation_behaviour(self):
        firstVersion = versioning.RIGSVersion.objects.get_for_object(self.event).latest('revision__date_created').parent
        diff = firstVersion.changes

        # Mainly to check for exceptions:
        self.assertTrue(len(diff.field_changes) > 0)

    def test_event_items(self):
        with reversion.create_revision():
            reversion.set_user(self.profile)
            item1 = models.EventItem.objects.create(event=self.event, name="TI I1", quantity=1, cost=1.00, order=1)
            self.event.save()

        # Find the most recent version
        currentVersion = versioning.RIGSVersion.objects.get_for_object(self.event).latest('revision__date_created')

        diffs = currentVersion.changes.item_changes

        self.assertEqual(len(diffs), 1)
        self.assertTrue(currentVersion.changes.items_changed)
        self.assertFalse(currentVersion.changes.fields_changed)
        self.assertTrue(currentVersion.changes.anything_changed)

        self.assertTrue(diffs[0].old is None)
        self.assertEqual(diffs[0].new.name, "TI I1")

        # Edit the item
        with reversion.create_revision():
            reversion.set_user(self.profile)
            item1.name = "New Name"
            item1.save()
            self.event.save()

        currentVersion = versioning.RIGSVersion.objects.get_for_object(self.event).latest('revision__date_created')

        diffs = currentVersion.changes.item_changes

        self.assertEqual(len(diffs), 1)

        self.assertEqual(diffs[0].old.name, "TI I1")
        self.assertEqual(diffs[0].new.name, "New Name")

        # Check the diff
        self.assertEqual(currentVersion.changes.item_changes[0].field_changes[0].diff,
                         [{'type': 'delete', 'text': "TI I1"},
                          {'type': 'insert', 'text': "New Name"},
                          ])

        # Delete the item

        with reversion.create_revision():
            item1.delete()
            self.event.save()

        # Find the most recent version
        currentVersion = versioning.RIGSVersion.objects.get_for_object(self.event).latest('revision__date_created')

        diffs = currentVersion.changes.item_changes

        self.assertEqual(len(diffs), 1)
        self.assertTrue(currentVersion.changes.items_changed)
        self.assertFalse(currentVersion.changes.fields_changed)
        self.assertTrue(currentVersion.changes.anything_changed)

        self.assertEqual(diffs[0].old.name, "New Name")
        self.assertTrue(diffs[0].new is None)

# Unit Tests


class TestVersioningViews(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.profile = models.Profile.objects.create(username="testuser1", email="1@test.com", is_superuser=True,
                                                    is_active=True, is_staff=True)

        cls.vatrate = models.VatRate.objects.create(start_at='2014-03-05', rate=0.20, comment='test1')

        cls.events = {}

        with reversion.create_revision():
            reversion.set_user(cls.profile)
            cls.events[1] = models.Event.objects.create(name="TE E1", start_date=date.today())

        with reversion.create_revision():
            reversion.set_user(cls.profile)
            cls.events[2] = models.Event.objects.create(name="TE E2", start_date='2014-03-05')

        with reversion.create_revision():
            reversion.set_user(cls.profile)
            cls.events[1].description = "A test description"
            cls.events[1].save()

        working = amodels.AssetStatus.objects.create(name="Working", should_show=True)
        broken = amodels.AssetStatus.objects.create(name="Broken", should_show=False)
        general = amodels.AssetCategory.objects.create(name="General")
        lighting = amodels.AssetCategory.objects.create(name="Lighting")

        cls.assets = {}

        with reversion.create_revision():
            reversion.set_user(cls.profile)
            cls.assets[1] = amodels.Asset.objects.create(asset_id="1991", description="Spaceflower", status=broken, category=lighting, date_acquired=date.today())

        with reversion.create_revision():
            reversion.set_user(cls.profile)
            cls.assets[2] = amodels.Asset.objects.create(asset_id="0001", description="Virgil", status=working, category=lighting, date_acquired=date.today())

        with reversion.create_revision():
            reversion.set_user(cls.profile)
            cls.assets[1].status = working
            cls.assets[1].save()

    def setUp(self):
        self.profile.set_password('testuser')
        self.profile.save()
        self.assertTrue(self.client.login(username=self.profile.username, password='testuser'))

    def test_history_loads_successfully(self):
        request_url = reverse('event_history', kwargs={'pk': self.events[1].pk})

        response = self.client.get(request_url, follow=True)
        self.assertEqual(response.status_code, 200)

        request_url = reverse('asset_history', kwargs={'pk': self.assets[1].asset_id})

        response = self.client.get(request_url, follow=True)
        self.assertEqual(response.status_code, 200)

    def test_activity_feed_loads_successfully(self):
        request_url = reverse('activity_feed')

        response = self.client.get(request_url, follow=True)
        self.assertEqual(response.status_code, 200)

    def test_activity_table_loads_successfully(self):
        request_url = reverse('activity_table')

        response = self.client.get(request_url, follow=True)
        self.assertEqual(response.status_code, 200)

        request_url = reverse('assets_activity_table')

        response = self.client.get(request_url, follow=True)
        self.assertEqual(response.status_code, 200)

    # Some edge cases that have caused server errors in the past
    def test_deleted_event(self):
        request_url = reverse('activity_feed')

        self.events[2].delete()

        response = self.client.get(request_url, follow=True)
        self.assertContains(response, "TE E2")
        self.assertEqual(response.status_code, 200)

    def test_deleted_relation(self):
        request_url = reverse('activity_feed')

        with reversion.create_revision():
            person = models.Person.objects.create(name="Test Person")
        with reversion.create_revision():
            self.events[1].person = person
            self.events[1].save()

        # Check response contains person
        response = self.client.get(request_url, follow=True)
        self.assertContains(response, "Test Person")
        self.assertEqual(response.status_code, 200)

        # Delete person
        person.delete()

        # Check response still contains person
        response = self.client.get(request_url, follow=True)
        self.assertContains(response, "Test Person")
        self.assertEqual(response.status_code, 200)

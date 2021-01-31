from datetime import date, timedelta, datetime, time
from decimal import *

import pytz
from django.conf import settings
from django.test import TestCase
from reversion import revisions as reversion

from RIGS import models


class ProfileTestCase(TestCase):
    def test_str(self):
        profile = models.Profile(first_name='Test', last_name='Case')
        self.assertEqual(str(profile), 'Test Case')
        profile.initials = 'TC'
        self.assertEqual(str(profile), 'Test Case "TC"')


class VatRateTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.rates = {
            0: models.VatRate.objects.create(start_at='2014-03-01', rate=0.20, comment='test1'),
            1: models.VatRate.objects.create(start_at='2016-03-01', rate=0.15, comment='test2'),
        }

    def test_find_correct(self):
        r = models.VatRate.objects.find_rate('2015-03-01')
        self.assertEqual(r, self.rates[0])
        r = models.VatRate.objects.find_rate('2016-03-01')
        self.assertEqual(r, self.rates[1])

    def test_percent_correct(self):
        self.assertEqual(self.rates[0].as_percent, 20)


class EventTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.all_events = set(range(1, 18))
        cls.current_events = (1, 2, 3, 6, 7, 8, 10, 11, 12, 14, 15, 16, 18)
        cls.not_current_events = set(cls.all_events) - set(cls.current_events)

        cls.vatrate = models.VatRate.objects.create(start_at='2014-03-05', rate=0.20, comment='test1')
        cls.profile = models.Profile.objects.create(username="testuser1", email="1@test.com")

        cls.events = {
            # produce 7 normal events - 5 current
            1: models.Event.objects.create(name="TE E1", start_date=date.today() + timedelta(days=6),
                                           description="start future no end"),
            2: models.Event.objects.create(name="TE E2", start_date=date.today(), description="start today no end"),
            3: models.Event.objects.create(name="TE E3", start_date=date.today(), end_date=date.today(),
                                           description="start today with end today"),
            4: models.Event.objects.create(name="TE E4", start_date='2014-03-20', description="start past no end"),
            5: models.Event.objects.create(name="TE E5", start_date='2014-03-20', end_date='2014-03-21',
                                           description="start past with end past"),
            6: models.Event.objects.create(name="TE E6", start_date=date.today() - timedelta(days=2),
                                           end_date=date.today() + timedelta(days=2),
                                           description="start past, end future"),
            7: models.Event.objects.create(name="TE E7", start_date=date.today() + timedelta(days=2),
                                           end_date=date.today() + timedelta(days=2),
                                           description="start + end in future"),

            # 2 cancelled - 1 current
            8: models.Event.objects.create(name="TE E8", start_date=date.today() + timedelta(days=2),
                                           end_date=date.today() + timedelta(days=2), status=models.Event.CANCELLED,
                                           description="cancelled in future"),
            9: models.Event.objects.create(name="TE E9", start_date=date.today() - timedelta(days=1),
                                           end_date=date.today() + timedelta(days=2), status=models.Event.CANCELLED,
                                           description="cancelled and started"),

            # 5 dry hire - 3 current
            10: models.Event.objects.create(name="TE E10", start_date=date.today(), dry_hire=True,
                                            description="dryhire today"),
            11: models.Event.objects.create(name="TE E11", start_date=date.today(), dry_hire=True,
                                            checked_in_by=cls.profile,
                                            description="dryhire today, checked in"),
            12: models.Event.objects.create(name="TE E12", start_date=date.today() - timedelta(days=1), dry_hire=True,
                                            status=models.Event.BOOKED, description="dryhire past"),
            13: models.Event.objects.create(name="TE E13", start_date=date.today() - timedelta(days=2), dry_hire=True,
                                            checked_in_by=cls.profile, description="dryhire past checked in"),
            14: models.Event.objects.create(name="TE E14", start_date=date.today(), dry_hire=True,
                                            status=models.Event.CANCELLED, description="dryhire today cancelled"),

            # 4 non rig - 3 current
            15: models.Event.objects.create(name="TE E15", start_date=date.today(), is_rig=False,
                                            description="non rig today"),
            16: models.Event.objects.create(name="TE E16", start_date=date.today() + timedelta(days=1), is_rig=False,
                                            description="non rig tomorrow"),
            17: models.Event.objects.create(name="TE E17", start_date=date.today() - timedelta(days=1), is_rig=False,
                                            description="non rig yesterday"),
            18: models.Event.objects.create(name="TE E18", start_date=date.today(), is_rig=False,
                                            status=models.Event.CANCELLED,
                                            description="non rig today cancelled"),
        }

    def test_count(self):
        # Santiy check we have the expected events created
        self.assertEqual(models.Event.objects.count(), 18, "Incorrect number of events, check setup")

    def test_rig_count(self):
        # Changed to not include unreturned dry hires in rig count
        self.assertEqual(models.Event.objects.rig_count(), 7)

    def test_current_events(self):
        current_events = models.Event.objects.current_events()
        self.assertEqual(len(current_events), len(self.current_events))
        for eid in self.current_events:
            self.assertIn(models.Event.objects.get(name="TE E%d" % eid), current_events)

        for eid in self.not_current_events:
            self.assertNotIn(models.Event.objects.get(name="TE E%d" % eid), current_events)

    def test_related_venue(self):
        v1 = models.Venue.objects.create(name="TE V1")
        v2 = models.Venue.objects.create(name="TE V2")

        e1 = []
        e2 = []
        for (key, event) in self.events.items():
            if event.pk % 2:
                event.venue = v1
                e1.append(event)
            else:
                event.venue = v2
                e2.append(event)
            event.save()

        self.assertCountEqual(e1, v1.latest_events)
        self.assertCountEqual(e2, v2.latest_events)

        for (key, event) in self.events.items():
            event.venue = None

    def test_related_vatrate(self):
        self.assertEqual(self.vatrate, models.Event.objects.all()[0].vat_rate)

    def test_related_person(self):
        p1 = models.Person.objects.create(name="TE P1")
        p2 = models.Person.objects.create(name="TE P2")

        e1 = []
        e2 = []
        for (key, event) in self.events.items():
            if event.pk % 2:
                event.person = p1
                e1.append(event)
            else:
                event.person = p2
                e2.append(event)
            event.save()

        self.assertCountEqual(e1, p1.latest_events)
        self.assertCountEqual(e2, p2.latest_events)

        for (key, event) in self.events.items():
            event.person = None

    def test_related_organisation(self):
        o1 = models.Organisation.objects.create(name="TE O1")
        o2 = models.Organisation.objects.create(name="TE O2")

        e1 = []
        e2 = []
        for (key, event) in self.events.items():
            if event.pk % 2:
                event.organisation = o1
                e1.append(event)
            else:
                event.organisation = o2
                e2.append(event)
            event.save()

        self.assertCountEqual(e1, o1.latest_events)
        self.assertCountEqual(e2, o2.latest_events)

        for (key, event) in self.events.items():
            event.organisation = None

    def test_organisation_person_join(self):
        p1 = models.Person.objects.create(name="TE P1")
        p2 = models.Person.objects.create(name="TE P2")
        o1 = models.Organisation.objects.create(name="TE O1")
        o2 = models.Organisation.objects.create(name="TE O2")

        events = models.Event.objects.all()
        # p1 in o1 + o2, p2 in o1
        for event in events[:2]:
            event.person = p1
            event.organisation = o1
            event.save()
        for event in events[3:4]:
            event.person = p1
            event.organisation = o2
            event.save()
        for event in events[5:7]:
            event.person = p2
            event.organisation = o1
            event.save()

        events = models.Event.objects.all()

        # Check person's organisations
        self.assertIn((o1, 2), p1.organisations)
        self.assertIn((o2, 1), p1.organisations)
        self.assertIn((o1, 2), p2.organisations)
        self.assertEqual(len(p2.organisations), 1)

        # Check organisation's persons
        self.assertIn((p1, 2), o1.persons)
        self.assertIn((p2, 2), o1.persons)
        self.assertIn((p1, 1), o2.persons)
        self.assertEqual(len(o2.persons), 1)

    def test_cancelled_property(self):
        edit = self.events[1]
        edit.status = models.Event.CANCELLED
        edit.save()
        event = models.Event.objects.get(pk=edit.pk)
        self.assertEqual(event.status, models.Event.CANCELLED)
        self.assertTrue(event.cancelled)
        event.status = models.Event.PROVISIONAL
        event.save()

    def test_confirmed_property(self):
        edit = self.events[1]
        edit.status = models.Event.CONFIRMED
        edit.save()
        event = models.Event.objects.get(pk=edit.pk)
        self.assertEqual(event.status, models.Event.CONFIRMED)
        self.assertTrue(event.confirmed)
        event.status = models.Event.PROVISIONAL
        event.save()

    def test_earliest_time(self):
        event = models.Event(name="TE ET", start_date=date(2016, 0o1, 0o1))

        # Just a start date
        self.assertEqual(event.earliest_time, date(2016, 0o1, 0o1))

        # With start time
        event.start_time = time(9, 00)
        self.assertEqual(event.earliest_time, self.create_datetime(2016, 1, 1, 9, 00))

        # With access time
        event.access_at = self.create_datetime(2015, 12, 0o3, 9, 57)
        self.assertEqual(event.earliest_time, event.access_at)

        # With meet time
        event.meet_at = self.create_datetime(2015, 12, 0o3, 9, 55)
        self.assertEqual(event.earliest_time, event.meet_at)

        # Check order isn't important
        event.start_date = date(2015, 12, 0o3)
        self.assertEqual(event.earliest_time, self.create_datetime(2015, 12, 0o3, 9, 00))

    def test_latest_time(self):
        event = models.Event(name="TE LT", start_date=date(2016, 0o1, 0o1))

        # Just start date
        self.assertEqual(event.latest_time, event.start_date)

        # Just end date
        event.end_date = date(2016, 1, 2)
        self.assertEqual(event.latest_time, event.end_date)

        # With end time
        event.end_time = time(23, 00)
        self.assertEqual(event.latest_time, self.create_datetime(2016, 1, 2, 23, 00))

    def test_in_bounds(self):
        manager = models.Event.objects
        events = [
            manager.create(name="TE IB0", start_date='2016-01-02'),  # yes no
            manager.create(name="TE IB1", start_date='2015-12-31', end_date='2016-01-04'),

            # basic checks
            manager.create(name='TE IB2', start_date='2016-01-02', end_date='2016-01-04'),
            manager.create(name='TE IB3', start_date='2015-12-31', end_date='2016-01-03'),
            manager.create(name='TE IB4', start_date='2016-01-04',
                           access_at=self.create_datetime(2016, 0o1, 0o3, 00, 00)),
            manager.create(name='TE IB5', start_date='2016-01-04',
                           meet_at=self.create_datetime(2016, 0o1, 0o2, 00, 00)),

            # negative check
            manager.create(name='TE IB6', start_date='2015-12-31', end_date='2016-01-01'),
        ]

        in_bounds = manager.events_in_bounds(self.create_datetime(2016, 1, 2, 0, 0),
                                             self.create_datetime(2016, 1, 3, 0, 0))
        self.assertIn(events[0], in_bounds)
        self.assertIn(events[1], in_bounds)
        self.assertIn(events[2], in_bounds)
        self.assertIn(events[3], in_bounds)
        self.assertIn(events[4], in_bounds)
        self.assertIn(events[5], in_bounds)

        self.assertNotIn(events[6], in_bounds)

    def create_datetime(self, year, month, day, hour, min):
        tz = pytz.timezone(settings.TIME_ZONE)
        return tz.localize(datetime(year, month, day, hour, min))


class EventItemTestCase(TestCase):
    def setUp(self):
        self.e1 = models.Event.objects.create(name="TI E1", start_date=date.today())
        self.e2 = models.Event.objects.create(name="TI E2", start_date=date.today())

    def test_item_cost(self):
        item = models.EventItem.objects.create(event=self.e1, name="TI I1", quantity=1, cost=1.00, order=1)
        self.assertEqual(item.total_cost, 1.00)

        item.cost = 2.50
        self.assertEqual(item.total_cost, 2.50)

        item.quantity = 4
        self.assertEqual(item.total_cost, 10.00)

        # need to tidy up
        item.delete()

    def test_item_order(self):
        i1 = models.EventItem.objects.create(event=self.e1, name="TI I1", quantity=1, cost=1.00, order=1)
        i2 = models.EventItem.objects.create(event=self.e1, name="TI I2", quantity=1, cost=1.00, order=2)

        items = self.e1.items.all()
        self.assertListEqual([i1, i2], list(items))


class EventPricingTestCase(TestCase):
    def setUp(self):
        models.VatRate.objects.create(rate=0.20, comment="TP V1", start_at='2013-01-01')
        models.VatRate.objects.create(rate=0.10, comment="TP V2", start_at=date.today() - timedelta(days=1))
        self.e1 = models.Event.objects.create(name="TP E1", start_date=date.today() - timedelta(days=2))
        self.e2 = models.Event.objects.create(name="TP E2", start_date=date.today())

        # Create some items E1, total 70.40
        # Create some items E2, total 381.20
        self.i1 = models.EventItem.objects.create(event=self.e1, name="TP I1", quantity=1, cost=50.00, order=1)
        self.i2 = models.EventItem.objects.create(event=self.e1, name="TP I2", quantity=2, cost=3.20, order=2)
        self.i3 = models.EventItem.objects.create(event=self.e1, name="TP I3", quantity=7, cost=2.00, order=3)
        self.i4 = models.EventItem.objects.create(event=self.e2, name="TP I4", quantity=2, cost=190.60, order=1)

    # Decimal type is needed here as that is what is returned from the model.
    # Using anything else results in a failure due to floating point arritmetic
    def test_sum_totals(self):
        self.assertEqual(self.e1.sum_total, Decimal('70.40'))
        self.assertEqual(self.e2.sum_total, Decimal('381.20'))

    def test_vat_rate(self):
        self.assertEqual(self.e1.vat_rate.rate, Decimal('0.20'))
        self.assertEqual(self.e2.vat_rate.rate, Decimal('0.10'))

    def test_vat_ammount(self):
        self.assertEqual(self.e1.vat, Decimal('14.08'))
        self.assertEqual(self.e2.vat, Decimal('38.12'))

    def test_grand_total(self):
        self.assertEqual(self.e1.total, Decimal('84.48'))
        self.assertEqual(self.e2.total, Decimal('419.32'))


class EventAuthorisationTestCase(TestCase):
    def setUp(self):
        models.VatRate.objects.create(rate=0.20, comment="TP V1", start_at='2013-01-01')
        self.profile = models.Profile.objects.get_or_create(
            first_name='Test',
            last_name='TEC User',
            username='eventauthtest',
            email='teccie@functional.test',
            is_superuser=True  # lazily grant all permissions
        )[0]
        self.person = models.Person.objects.create(name='Authorisation Test Person')
        self.organisation = models.Organisation.objects.create(name='Authorisation Test Organisation', union_account=True)
        self.event = models.Event.objects.create(name="AuthorisationTestCase", person=self.person, organisation=self.organisation,
                                                 start_date=date.today())
        # Add some items
        models.EventItem.objects.create(event=self.event, name="Authorisation test item", quantity=2, cost=123.45,
                                        order=1)

    def test_event_property(self):
        auth1 = models.EventAuthorisation.objects.create(event=self.event, email="authorisation@model.test.case",
                                                         name="Test Auth 1", amount=self.event.total - 1,
                                                         sent_by=self.profile)
        self.assertFalse(self.event.authorised)
        auth1.amount = self.event.total
        auth1.save()
        self.assertTrue(self.event.authorised)

    def test_last_edited(self):
        with reversion.create_revision():
            auth = models.EventAuthorisation.objects.create(event=self.event, email="authorisation@model.test.case",
                                                            name="Test Auth", amount=self.event.total,
                                                            sent_by=self.profile)
        self.assertIsNotNone(auth.last_edited_at)

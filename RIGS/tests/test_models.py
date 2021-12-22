from datetime import date, timedelta, datetime, time
from decimal import *

import pytz
import pytest
from django.conf import settings
from django.test import TestCase
from reversion import revisions as reversion

from RIGS import models


def assert_decimal_equality(d1, d2):
    assert float(d1) == pytest.approx(float(d2))


def test_str():
    profile = models.Profile(first_name='Test', last_name='Case')
    assert str(profile) == 'Test Case'
    profile.initials = 'TC'
    assert str(profile) == 'Test Case "TC"'


@pytest.mark.django_db
def test_find_correct(vat_rate):
    new_rate = models.VatRate.objects.create(start_at='2016-03-01', rate=0.15, comment='test2')
    r = models.VatRate.objects.find_rate('2015-03-01')
    assert_decimal_equality(r.rate, vat_rate.rate)
    r = models.VatRate.objects.find_rate('2016-03-01')
    assert_decimal_equality(r.rate, new_rate.rate)


def test_percent_correct(vat_rate):
    assert vat_rate.as_percent == 20


def test_related_vatrate(basic_event, vat_rate):
    assert_decimal_equality(vat_rate.rate, basic_event.vat_rate.rate)


class EventTest():
    def test_count(many_events):
        # Sanity check we have the expected events created
        assert models.Event.objects.count() == 18

    def test_rig_count(many_events):
        # Changed to not include unreturned dry hires in rig count
        assert models.Event.objects.rig_count() == 7

    def test_current_events(many_events):
        all_events = set(range(1, 18))
        current_events = (1, 2, 3, 6, 7, 8, 10, 11, 12, 14, 15, 16, 18)
        not_current_events = set(cls.all_events) - set(cls.current_events)
        current_events = models.Event.objects.current_events()
        assert len(current_events) == len(self.current_events)
        for eid in current_events:
            assert models.Event.objects.get(name="TE E%d" % eid) in current_events

        for eid in not_current_events:
            assert models.Event.objects.get(name="TE E%d" % eid) not in current_events

    def test_related(many_events):
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

        assert set(e1) == set(v1.latest_events)
        assert set(e2) == set(v2.latest_events)
        # Cleanup
        v1.delete()
        v2.delete()

    def test_related_person(many_events):
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

        assert set(e1) == set(p1.latest_events)
        assert set(e2) == set(p2.latest_events)

        p1.delete()
        p2.delete()

    def test_related_organisation(many_events):
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

        assert set(e1) == set(o1.latest_events)
        assert set(e1) == set(o2.latest_events)

        for (key, event) in self.events.items():
            event.organisation = None

    def test_organisation_person_join(many_events):
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
        assert (o1, 2) in p1.organisations
        assert (o2, 1) in p1.organisations
        assert (o1, 2) in p2.organisations
        assert len(p2.organisations) == 1

        # Check organisation's persons
        assert (p1, 2) in o1.persons
        assert (p2, 2) in o1.persons
        assert (p1, 1) in o2.persons
        assert len(o2.persons) == 1

    def test_cancelled_property(many_events):
        edit = many_events[1]
        edit.status = models.Event.CANCELLED
        edit.save()
        event = models.Event.objects.get(pk=edit.pk)
        assert event.status == models.Event.CANCELLED
        assert event.cancelled
        event.status = models.Event.PROVISIONAL
        event.save()

    def test_confirmed_property(many_events):
        edit = many_events[1]
        edit.status = models.Event.CONFIRMED
        edit.save()
        event = models.Event.objects.get(pk=edit.pk)
        assert event.status == models.Event.CONFIRMED
        assert event.confirmed
        event.status = models.Event.PROVISIONAL
        event.save()


def test_earliest_time():
    event = models.Event(name="TE ET", start_date=date(2016, 0o1, 0o1))

    # Just a start date
    assert event.earliest_time == date(2016, 0o1, 0o1)

    # With start time
    event.start_time = time(9, 00)
    assert event.earliest_time == create_datetime(2016, 1, 1, 9, 00)

    # With access time
    event.access_at = create_datetime(2015, 12, 0o3, 9, 57)
    assert event.earliest_time == event.access_at

    # With meet time
    event.meet_at = create_datetime(2015, 12, 0o3, 9, 55)
    assert event.earliest_time == event.meet_at

    # Check order isn't important
    event.start_date = date(2015, 12, 0o3)
    assert event.earliest_time == create_datetime(2015, 12, 0o3, 9, 00)


def test_latest_time():
    event = models.Event(name="TE LT", start_date=date(2016, 0o1, 0o1))

    # Just start date
    assert event.latest_time == event.start_date

    # Just end date
    event.end_date = date(2016, 1, 2)
    assert event.latest_time == event.end_date

    # With end time
    event.end_time = time(23, 00)
    assert event.latest_time == create_datetime(2016, 1, 2, 23, 00)


def test_in_bounds():
    manager = models.Event.objects
    events = [
        manager.create(name="TE IB0", start_date='2016-01-02'),  # yes no
        manager.create(name="TE IB1", start_date='2015-12-31', end_date='2016-01-04'),

        # basic checks
        manager.create(name='TE IB2', start_date='2016-01-02', end_date='2016-01-04'),
        manager.create(name='TE IB3', start_date='2015-12-31', end_date='2016-01-03'),
        manager.create(name='TE IB4', start_date='2016-01-04',
                       access_at=create_datetime(2016, 0o1, 0o3, 00, 00)),
        manager.create(name='TE IB5', start_date='2016-01-04',
                       meet_at=create_datetime(2016, 0o1, 0o2, 00, 00)),

        # negative check
        manager.create(name='TE IB6', start_date='2015-12-31', end_date='2016-01-01'),
    ]

    in_bounds = manager.events_in_bounds(create_datetime(2016, 1, 2, 0, 0),
                                         create_datetime(2016, 1, 3, 0, 0))
    assert events[0] in in_bounds
    assert events[1], in_bounds
    assert events[2], in_bounds
    assert events[3], in_bounds
    assert events[4], in_bounds
    assert events[5], in_bounds

    assert events[6] not in in_bounds


def create_datetime(year, month, day, hour, minute):
    tz = pytz.timezone(settings.TIME_ZONE)
    return tz.localize(datetime(year, month, day, hour, minute))


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

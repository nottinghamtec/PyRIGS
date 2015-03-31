from django.test import TestCase
from RIGS import models
from datetime import date, timedelta

class VatRateTestCase(TestCase):
	def setUp(self):
		models.VatRate.objects.create(start_at='2014-03-01',rate=0.20,comment='test1')
		models.VatRate.objects.create(start_at='2016-03-01',rate=0.15,comment='test2')

	def test_find_correct(self):
		r = models.VatRate.objects.find_rate('2015-03-01')
		self.assertEqual(r.comment, 'test1')
		r = models.VatRate.objects.find_rate('2016-03-01')
		self.assertEqual(r.comment, 'test2')

	def test_percent_correct(self):
		r = models.VatRate.objects.get(rate=0.20)
		self.assertEqual(r.as_percent, 20)

class EventTestCase(TestCase):
	def setUp(self):
		self.vatrate = models.VatRate.objects.create(start_at='2014-03-05',rate=0.20,comment='test1')
		self.profile = models.Profile.objects.create(username="testuser1", email="1@test.com")

		# produce 7 normal events
		models.Event.objects.create(name="TE E1", start_date=date.today() + timedelta(days=6), description="start future no end") 
		models.Event.objects.create(name="TE E2", start_date=date.today(), description="start today no end")
		models.Event.objects.create(name="TE E3", start_date=date.today(), end_date=date.today(), description="start today with end")
		models.Event.objects.create(name="TE E4", start_date='2014-03-20', description="start past no end")
		models.Event.objects.create(name="TE E5", start_date='2014-03-20', end_date='2014-03-21', description="start past with end")
		models.Event.objects.create(name="TE E6", start_date=date.today()-timedelta(days=2), end_date=date.today()+timedelta(days=2), description="start past, end future")
		models.Event.objects.create(name="TE E7", start_date=date.today()+timedelta(days=2), end_date=date.today()+timedelta(days=2), description="start + end in future")

		# 2 cancelled
		models.Event.objects.create(name="TE E8", start_date=date.today()+timedelta(days=2), end_date=date.today()+timedelta(days=2), status=models.Event.CANCELLED, description="cancelled in future")
		models.Event.objects.create(name="TE E9", start_date=date.today()-timedelta(days=1), end_date=date.today()+timedelta(days=2), status=models.Event.CANCELLED, description="cancelled and started")

		# 5 dry hire
		models.Event.objects.create(name="TE E10", start_date=date.today(), dry_hire=True, description="dryhire today")
		models.Event.objects.create(name="TE E11", start_date=date.today(), dry_hire=True, checked_in_by=self.profile, description="dryhire today, checked in")
		models.Event.objects.create(name="TE E12", start_date=date.today()-timedelta(days=1), dry_hire=True, description="dryhire past")
		models.Event.objects.create(name="TE E13", start_date=date.today()-timedelta(days=1), dry_hire=True, checked_in_by=self.profile, description="dryhire past checked in")
		models.Event.objects.create(name="TE E14", start_date=date.today(), dry_hire=True, status=models.Event.CANCELLED, description="dryhire today cancelled")

		# 4 non rig
		models.Event.objects.create(name="TE E15", start_date=date.today(), is_rig=False, description="non rig today")
		models.Event.objects.create(name="TE E16", start_date=date.today()+timedelta(days=1), is_rig=False, description="non rig tomorrow")
		models.Event.objects.create(name="TE E17", start_date=date.today()-timedelta(days=1), is_rig=False, description="non rig yesterday")
		models.Event.objects.create(name="TE E18", start_date=date.today(), is_rig=False, status=models.Event.CANCELLED, description="non rig today cancelled")
	
	def test_count(self):
		# Santiy check we have the expected events created
		self.assertEqual(models.Event.objects.count(), 18, "Incorrect number of events, check setup")

	def test_rig_count(self):
		# by my count this is 7
		self.assertEqual(models.Event.objects.rig_count(), 7)

	def test_current_events(self):
		# by my count 7 + 4 + 1
		current_events = models.Event.objects.current_events()
		# for event in current_events:
		# 	print event
		self.assertEqual(len(current_events), 7+4+1)
		self.assertIn(models.Event.objects.get(name="TE E12"), current_events)

	def test_related_venue(self):
		v1 = models.Venue.objects.create(name="TE V1")
		v2 = models.Venue.objects.create(name="TE V2")
		events = models.Event.objects.all()
		for event in events[:2]:
			event.venue = v1
			event.save()
		for event in events[3:4]:
			event.venue = v2
			event.save()

		events = models.Event.objects.all()
		self.assertItemsEqual(events[:2], v1.latest_events)
		self.assertItemsEqual(events[3:4], v2.latest_events)

	def test_related_vatrate(self):
		self.assertEqual(self.vatrate, models.Event.objects.all()[0].vat_rate)

	def test_cancelled_property(self):
		event = models.Event.objects.all()[0]
		event.status = models.Event.CANCELLED
		event.save()
		event = models.Event.objects.all()[0]
		self.assertEqual(event.status, models.Event.CANCELLED)
		self.assertTrue(event.cancelled)
		event.status = models.Event.PROVISIONAL
		event.save()

	def test_confirmed_property(self):
		event = models.Event.objects.all()[0]
		event.status = models.Event.CONFIRMED
		event.save()
		event = models.Event.objects.all()[0]
		self.assertEqual(event.status, models.Event.CONFIRMED)
		self.assertTrue(event.confirmed)
		event.status = models.Event.PROVISIONAL
		event.save()
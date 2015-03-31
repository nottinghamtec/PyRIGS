from django.test import TestCase
from RIGS import models

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
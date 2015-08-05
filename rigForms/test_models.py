from django.test import TestCase
from rigForms import models

class FormModelsTestCase(TestCase):
	def setUp(self):
		self.schemaType1 = models.Type.objects.create(name="Test Type",description="Description of a test type")
		models.Schema.objects.create(start_at='2014-03-01',comment='test1', schema_type=self.schemaType1)
		models.Schema.objects.create(start_at='2016-03-01',comment='test2', schema_type=self.schemaType1)

		self.schemaType2 = models.Type.objects.create(name="Test Type 2",description="Description of the second test type")
		models.Schema.objects.create(start_at='2014-03-01',comment='test3', schema_type=self.schemaType2)
		models.Schema.objects.create(start_at='2016-03-01',comment='test4', schema_type=self.schemaType2)

	def test_find_correct(self):
		r = models.Schema.objects.find_schema(self.schemaType1, '2015-03-01')
		self.assertEqual(r.comment, 'test1')
		r = models.Schema.objects.find_schema(self.schemaType1, '2016-03-01')
		self.assertEqual(r.comment, 'test2')
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.core.exceptions import ObjectDoesNotExist, ValidationError
import reversion

import json
import jsonschema

import datetime

from RIGS.models import RevisionMixin


@reversion.register
class Type(models.Model, RevisionMixin):
    name = models.CharField(max_length=255, blank=False, null=False)
    description = models.CharField(max_length=255, blank=True, null=True)
    active = models.BooleanField(default=True)

class SchemaManager(models.Manager):
    def current_schema(self, schemaType):
        return self.find_schema(schemaType, datetime.datetime.now())

    def find_schema(self, schemaType, date):
        return self.filter(schema_type=schemaType, start_at__lte=date).latest()

@reversion.register
@python_2_unicode_compatible
class Schema(models.Model, RevisionMixin):
	schema_type = models.ForeignKey('Type', related_name='schemas', blank=False)

	start_at = models.DateTimeField()
    
	schema = models.TextField(blank=False, null=False, default="{}")
	layout = models.TextField(blank=False, null=False, default="[]")

	comment = models.CharField(max_length=255)

	objects = SchemaManager()

	def clean(self):
		# raise ValidationError('Invalid JSON received') 
		try: 
			jsonData = json.loads(self.schema)
		except ValueError:
			raise ValidationError('Invalid JSON in schema')
		except:
			raise

		try: 
			jsonData = json.loads('{"data":'+self.layout+"}")
		except ValueError:
			raise ValidationError('Invalid JSON in layout')
		except:
			raise

	def save(self, *args, **kwargs):
		"""Call :meth:`full_clean` before saving."""
		self.full_clean()
		super(Schema, self).save(*args, **kwargs)

	class Meta:
		ordering = ['-start_at']
		get_latest_by = 'start_at'

	def __str__(self):
		return self.schema_type.name + "|" + self.comment + " " + str(self.start_at)

@reversion.register
class Form(models.Model, RevisionMixin):
	event = models.ForeignKey('RIGS.Event', related_name='forms', blank=False)
	schema = models.ForeignKey('Schema', related_name='forms', blank=False)

	data = models.TextField(blank=False, null=False, default="{}")

	def clean(self):
		try: 
			jsonData = json.loads(self.data)
		except ValueError:
			raise ValidationError('Invalid JSON received from browser')

		try:
			schemaValue = json.loads(self.schema.schema)
			jsonschema.validate(jsonData,schemaValue) #This will raise ValidationError if data doesn't match schema
		except ObjectDoesNotExist:
			pass #halfway through creation this can cause issues
		except ValueError:
			raise ValidationError('Invalid JSON in schema, cannot validate')
		except jsonschema.ValidationError: #raise a django exception
			raise ValidationError('Data is not valid, cannot save')


	def save(self, *args, **kwargs):
		"""Call :meth:`full_clean` before saving."""
		self.full_clean()
		super(Form, self).save(*args, **kwargs)

	class Meta:
		permissions = (
			('create_form', 'Can complete a form'),
            ('update_form', 'Can change a form'),
            ('view_form', 'Can view forms'),
		)
		
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
import reversion

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
    layout = models.TextField(blank=False, null=False, default="{}")

    comment = models.CharField(max_length=255)

    objects = SchemaManager()

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

	class Meta:
		permissions = (
			('create_form', 'Can complete a form'),
            ('update_form', 'Can change a form'),
            ('view_form', 'Can view forms'),
		)
		
from django.db import models
from django.conf import settings
import reversion

# Create your models here.


@reversion.register
class TrainingCategory(models.Model):
    category_number = models.PositiveSmallIntegerField()
    category_name = models.CharField(max_length=50)


@reversion.register
class TrainingItem(models.Model):
    category = models.ForeignKey(TrainingCategory)
    item_number = models.PositiveSmallIntegerField()
    item_name = models.CharField(max_length=100)
    training_records = models.ManyToManyField(settings.AUTH_USER_MODEL,
                                              through_fields='finance.TrainingRecord')


@reversion.register
class TrainingRecord(models.Model):
    started_date = models.DateField(blank=True, null=True)
    started_user = models.ForeignKey(settings.AUTH_USER_MODEL)
    started_notes = models.TextField(blank=True, null=True)
    completed_date = models.DateField(blank=True, null=True)
    completed_user = models.ForeignKey(settings.AUTH_USER_MODEL)
    completed_notes = models.TextField(blank=True, null=True)
    assessed_date = models.DateField(blank=True, null=True)
    assessed_user = models.ForeignKey(settings.AUTH_USER_MODEL)
    assessed_notes = models.TextField(blank=True, null=True)


@reversion.register
class TrainingLevelRecord(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL)

    technical_assistant = models.DateField(blank=True, null=True)

    sound_technician = models.DateField(blank=True, null=True)
    sound_supervisor = models.DateField(blank=True, null=True)

    lighting_technician = models.DateField(blank=True, null=True)
    lighting_supervisor = models.DateField(blank=True, null=True)

    power_technician = models.DateField(blank=True, null=True)
    power_supervisor = models.DateField(blank=True, null=True)

    haulage_supervisor = models.DateField(blank=True, null=True)

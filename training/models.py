from django.db import models
from django.conf import settings
from django.utils.encoding import python_2_unicode_compatible
import reversion

# Create your models here.


@python_2_unicode_compatible
@reversion.register
class TrainingCategory(models.Model):
    category_number = models.PositiveSmallIntegerField()
    category_name = models.CharField(max_length=50)

    def __str__(self):
        return "{0}: {1}".format(self.category_number, self.category_name)


@python_2_unicode_compatible
@reversion.register
class TrainingItem(models.Model):
    category = models.ForeignKey(TrainingCategory)
    item_number = models.PositiveSmallIntegerField()
    item_name = models.CharField(max_length=100)
    training_records = models.ManyToManyField(settings.AUTH_USER_MODEL,
                                              through='TrainingRecord', through_fields=('training_item', 'trainee'))

    def __str__(self):
        return "{0}.{1}: {2}".format(self.category.category_number, self.item_number, self.item_name)


@python_2_unicode_compatible
@reversion.register
class TrainingRecord(models.Model):
    trainee = models.ForeignKey(settings.AUTH_USER_MODEL)
    training_item = models.ForeignKey(TrainingItem)

    started_date = models.DateField(blank=True, null=True)
    started_trainer = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='trainingrecords_started', blank=True, null=True)
    started_notes = models.TextField(blank=True, null=True)
    completed_date = models.DateField(blank=True, null=True)
    completed_trainer = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='trainingrecords_completed', blank=True, null=True)
    completed_notes = models.TextField(blank=True, null=True)
    assessed_date = models.DateField(blank=True, null=True)
    assessed_trainer = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='trainingrecords_assessed', blank=True, null=True)
    assessed_notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return "{0} - {1}".format(self.trainee, self.training_item)

    class Meta:
        unique_together = ('trainee', 'training_item')


@python_2_unicode_compatible
@reversion.register
class TrainingLevelRecord(models.Model):
    trainee = models.ForeignKey(settings.AUTH_USER_MODEL)

    technical_assistant = models.DateField(blank=True, null=True)

    sound_technician = models.DateField(blank=True, null=True)
    sound_supervisor = models.DateField(blank=True, null=True)

    lighting_technician = models.DateField(blank=True, null=True)
    lighting_supervisor = models.DateField(blank=True, null=True)

    power_technician = models.DateField(blank=True, null=True)
    power_supervisor = models.DateField(blank=True, null=True)

    haulage_supervisor = models.DateField(blank=True, null=True)

    def __str__(self):
        return "{0}".format(self.trainee)

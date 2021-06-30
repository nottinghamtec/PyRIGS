from django.db import models

from RIGS.models import RevisionMixin, Profile
from reversion import revisions as reversion

# 'shim' overtop the profile model to neatly contain all training related fields etc
@reversion.register
class Trainee(Profile):
    pass

# Items
class TrainingCategory(models.Model):
    number = models.CharField(max_length=3)
    name = models.CharField(max_length=50)


class TrainingItem(models.Model):
    category = models.ForeignKey('TrainingCategory', on_delete=models.RESTRICT)
    number = models.CharField(max_length=3)
    name = models.CharField(max_length=50)


# TODO Validation that dates cannot be in the future
class TrainingItemQualification(models.Model):
    STARTED = 0
    COMPLETE = 1
    PASSED_OUT = 2
    CHOICES = (
        (STARTED, 'Training Started'),
        (COMPLETE, 'Training Complete'),
        (PASSED_OUT, 'Passed Out'),
    )
    item = models.ForeignKey('TrainingItem', on_delete=models.RESTRICT)
    trainee = models.ForeignKey('Trainee', related_name='items', on_delete=models.RESTRICT)    
    depth = models.IntegerField(choices=CHOICES)
    date = models.DateTimeField()
    supervisor = models.ForeignKey('Trainee', related_name='training_started', on_delete=models.RESTRICT)
    notes = models.TextField()


# Levels
class TrainingLevel(models.Model, RevisionMixin):
    ASSISTANT = 0
    TECHNICIAN = 1
    SUPERVISOR = 2
    CHOICES = (
        (ASSISTANT, 'Technical Assistant'),
        (TECHNICIAN, 'Technician'),
        (SUPERVISOR, 'Supervisor'),
    )
    department = models.CharField(max_length=50, null=True) # Technical Assistant does not have a department
    level = models.IntegerField(choices=CHOICES)


class TrainingLevelQualification(models.Model):
    trainee = models.ForeignKey('Trainee', related_name='levels', on_delete=models.RESTRICT)   
    level = models.ForeignKey('TrainingLevel', on_delete=models.RESTRICT)
    confirmed_on = models.DateTimeField()
    confirmed_by = models.ForeignKey('Trainee', related_name='confirmer', on_delete=models.RESTRICT)

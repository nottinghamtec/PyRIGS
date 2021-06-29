from django.db import models

from RIGS.models import RevisionMixin, Profile
from reversion import revisions as reversion

# 'shim' overtop the profile model to neatly contain all training related fields etc
@reversion.register
class Trainee(Profile):
    pass

# Items
class TrainingCategory(models.Model):
    number = models.CharField(max_length=3) # Does this 1:1 correspond with a department? I think the answer is sometimes...
    name = models.CharField(max_length=50)


class TrainingItem(models.Model):
    category = models.ForeignKey('TrainingCategory', on_delete=models.CASCADE)
    number = models.CharField(max_length=3)
    name = models.CharField(max_length=50)


class TrainingItemInstance(models.Model):
    item = models.ForeignKey('TrainingItem', on_delete=models.CASCADE)
    trainee = models.ForeignKey('Trainee', related_name='items', on_delete=models.CASCADE)    

    training_started_on = models.DateField()
    training_started_by = models.ForeignKey('Trainee', related_name='training_started', on_delete=models.CASCADE)
    
    training_complete_on = models.DateField()
    training_complete_by = models.ForeignKey('Trainee', related_name='training_complete', on_delete=models.CASCADE)

    passed_out_on = models.DateField()
    passed_out_by = models.ForeignKey('Trainee', related_name='passed_out', on_delete=models.CASCADE)


class Department(models.Model):
    name = models.CharField(max_length=50)


# Levels
class TrainingLevel(models.Model, RevisionMixin):
    requirements = models.ManyToManyField(TrainingItem)

    class Meta:
        abstract = True

@reversion.register
class TechnicalAssistant(TrainingLevel):
    # department = models.ForeignKey('Department', on_delete=models.CASCADE)
    pass


@reversion.register
class Technician(TrainingLevel):
    department = models.ForeignKey('Department', on_delete=models.CASCADE)


@reversion.register
class Supervisor(TrainingLevel):
    department = models.ForeignKey('Department', on_delete=models.CASCADE)

from django.db import models

from RIGS.models import RevisionMixin, Profile
from reversion import revisions as reversion

# 'shim' overtop the profile model to neatly contain all training related fields etc
class Trainee(Profile):
    class Meta:
        proxy = True

    def get_records_of_depth(self, depth):
        return self.qualifications_obtained.filter(depth=depth)

# Items
class TrainingCategory(models.Model):
    reference_number = models.CharField(max_length=3)
    name = models.CharField(max_length=50)


class TrainingItem(models.Model):
    reference_number = models.CharField(max_length=3)
    category = models.ForeignKey('TrainingCategory', related_name='items', on_delete=models.RESTRICT)    
    name = models.CharField(max_length=50)

    def __str__(self):
        return "{}.{} {}".format(self.category.reference_number, self.reference_number, self.name)


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
    trainee = models.ForeignKey('Trainee', related_name='qualifications_obtained', on_delete=models.RESTRICT)    
    depth = models.IntegerField(choices=CHOICES)
    date = models.DateField()
    # TODO Remember that some training is external. Support for making an organisation the trainer? 
    supervisor = models.ForeignKey('Trainee', related_name='qualifications_granted', on_delete=models.RESTRICT)
    notes = models.TextField(blank=True)


# Levels
# FIXME Common Competencies...
class TrainingLevel(models.Model, RevisionMixin):
    CHOICES = (
        (0, 'Technical Assistant'),
        (1, 'Technician'),
        (2, 'Supervisor'),
    )
    department = models.CharField(max_length=50, null=True) # N.B. Technical Assistant does not have a department
    level = models.IntegerField(choices=CHOICES)


class TrainingLevelQualification(models.Model):
    trainee = models.ForeignKey('Trainee', related_name='levels', on_delete=models.RESTRICT)   
    level = models.ForeignKey('TrainingLevel', on_delete=models.RESTRICT)
    confirmed_on = models.DateTimeField()
    confirmed_by = models.ForeignKey('Trainee', related_name='confirmer', on_delete=models.RESTRICT)

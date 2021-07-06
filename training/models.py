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

    class Meta:
        verbose_name_plural = 'Training Categories'

class TrainingItem(models.Model):
    reference_number = models.CharField(max_length=3)
    category = models.ForeignKey('TrainingCategory', related_name='items', on_delete=models.RESTRICT)    
    name = models.CharField(max_length=50)

    def __str__(self):
        return "{}.{} {}".format(self.category.reference_number, self.reference_number, self.name)


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

    def __str__(self):
        return "{} in {} on {}".format(self.depth, self.item, self.date)


# Levels
class TrainingLevel(models.Model, RevisionMixin):
    description = models.CharField(max_length=120, blank=True)
    TA = 0
    TECHNICIAN = 1
    SUPERVISOR = 2
    CHOICES = (
        (TA, 'Technical Assistant'),
        (TECHNICIAN, 'Technician'),
        (SUPERVISOR, 'Supervisor'),
    )
    DEPARTMENTS = (
        (0, 'Sound'),
        (1, 'Lighting'),
        (2, 'Power'),
        (3, 'Rigging'),
        (4, 'Haulage'),
    )
    department = models.IntegerField(choices=DEPARTMENTS, null=True) # N.B. Technical Assistant does not have a department
    level = models.IntegerField(choices=CHOICES)
    prerequisite_levels = models.ManyToManyField('self', related_name='prerequisites', symmetrical=False, blank=True)

    def get_requirements_of_depth(self, depth):
        return self.requirements.filter(depth=depth)

    @property
    def started_requirements(self):
        return self.get_requirements_of_depth(TrainingItemQualification.STARTED)

    @property
    def complete_requirements(self):
        return self.get_requirements_of_depth(TrainingItemQualification.COMPLETE)

    @property
    def passed_out_requirements(self):
        return self.get_requirements_of_depth(TrainingItemQualification.PASSED_OUT)

    def __str__(self):
        if self.department is None: # 2TA
            return self.get_level_display()
        else:
            return "{} {}".format(self.get_department_display(), self.get_level_display())

class TrainingLevelRequirement(models.Model):
    level = models.ForeignKey('TrainingLevel', related_name='requirements', on_delete=models.RESTRICT)
    item = models.ForeignKey('TrainingItem', on_delete=models.RESTRICT)
    depth = models.IntegerField(TrainingItemQualification.CHOICES)

    def __str__(self):
        return "{} in {}".format(TrainingItemQualification.CHOICES[self.depth][1], self.item)


class TrainingLevelQualification(models.Model):
    trainee = models.ForeignKey('Trainee', related_name='levels', on_delete=models.RESTRICT)   
    level = models.ForeignKey('TrainingLevel', on_delete=models.RESTRICT)
    confirmed_on = models.DateTimeField()
    confirmed_by = models.ForeignKey('Trainee', related_name='confirmer', on_delete=models.RESTRICT)

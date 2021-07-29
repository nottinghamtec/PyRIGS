from django.db import models

from RIGS.models import RevisionMixin, Profile
from reversion import revisions as reversion

# 'shim' overtop the profile model to neatly contain all training related fields etc
class Trainee(Profile):
    class Meta:
        proxy = True

    @property
    def is_supervisor(self):
        for level_qualification in self.levels.select_related('level').all():
            if confirmed_on is not None and level_qualification.level.level >= TrainingLevel.SUPERVISOR:
                return True

    def get_records_of_depth(self, depth):
        return self.qualifications_obtained.filter(depth=depth).select_related('item', 'trainee', 'supervisor')

    def is_user_qualified_in(self, item, required_depth):
        qual = self.qualifications_obtained.filter(item=item).first()  # this is a somewhat ghetto version of get_or_none
        return qual is not None and qual.depth >= required_depth

# Items
class TrainingCategory(models.Model):
    reference_number = models.CharField(max_length=3)
    name = models.CharField(max_length=50)

    def __str__(self):
        return "{}. {}".format(self.reference_number, self.name)

    class Meta:
        verbose_name_plural = 'Training Categories'

class TrainingItem(models.Model):
    reference_number = models.CharField(max_length=3)
    category = models.ForeignKey('TrainingCategory', related_name='items', on_delete=models.RESTRICT)    
    name = models.CharField(max_length=50)

    def __str__(self):
        return "{}.{} {}".format(self.category.reference_number, self.reference_number, self.name)

    @staticmethod
    def user_has_qualification(item, user, depth):
        for q in user.qualifications_obtained.all().select_related('item'):
            if q.item == item and q.depth > depth:
                return True


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
    # TODO Maximum depth - some things stop at Complete and you can't be passed out in them

    def __str__(self):
        return "{} in {} on {}".format(self.depth, self.item, self.date)

    def save(self, *args, **kwargs):
        super().save()
        for level in TrainingLevel.objects.all(): # Mm yes efficiency
            if level.user_has_requirements(self.trainee):
                level_qualification = TrainingLevelQualification.objects.create(trainee=self.trainee, level=level)


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

    def percentage_complete(self, user): # FIXME
        needed_qualifications = self.requirements.all().select_related()
        relavant_qualifications = 0.0
        # TODO Efficiency...
        for req in needed_qualifications:
            if user.is_user_qualified_in(req.item, req.depth):
                relavant_qualifications += 1.0

        if len(needed_qualifications) > 0:
            return int(relavant_qualifications / float(len(needed_qualifications)) * 100)
        else:
            return 0

    def user_has_requirements(self, user):
        return all(TrainingItem.user_has_qualification(req.item, user, req.depth) for req in self.requirements.select_related().all())            

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
    confirmed_on = models.DateTimeField(null=True)
    confirmed_by = models.ForeignKey('Trainee', related_name='confirmer', on_delete=models.RESTRICT, null=True)

    def __str__(self):
        return "{} qualified as a {}".format(self.trainee, self.level)

    class Meta:
        unique_together = ["trainee", "level"]

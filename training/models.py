from django.db import models

from RIGS.models import RevisionMixin, Profile
from reversion import revisions as reversion
from django.urls import reverse

from django.utils.safestring import SafeData, mark_safe


@reversion.register(for_concrete_model=False)
class Trainee(Profile, RevisionMixin):
    class Meta:
        proxy = True

    # FIXME use queryset
    def started_levels(self):
        return [level for level in TrainingLevel.objects.all() if level.percentage_complete(self) > 0 and level.pk not in self.level_qualifications.values_list('level', flat=True)]

    @property
    def is_technician(self):
        return self.level_qualifications.exclude(confirmed_on=None).select_related('level') \
             .filter(level__level=TrainingLevel.TECHNICIAN) \
             .exclude(level__department=TrainingLevel.HAULAGE) \
             .exclude(level__department__isnull=True).exists()


    @property
    def is_supervisor(self):
        return self.level_qualifications.exclude(confirmed_on=None).select_related('level') \
            .filter(level__level__gte=TrainingLevel.SUPERVISOR) \
            .exclude(level__department=TrainingLevel.HAULAGE) \
            .exclude(level__department__isnull=True).exists()

    @property
    def is_driver(self):
        return self.level_qualifications.all().exclude(confirmed_on=None).select_related('level').filter(level__department=TrainingLevel.HAULAGE).exists()

    def get_records_of_depth(self, depth):
        return self.qualifications_obtained.filter(depth=depth).select_related('item', 'trainee', 'supervisor')

    def is_user_qualified_in(self, item, required_depth):
        return self.qualifications_obtained.values('item', 'depth').filter(item=item).filter(depth__gte=required_depth).first() is not None  # this is a somewhat ghetto version of get_or_none

    def get_absolute_url(self):
        return reverse('trainee_detail', kwargs={'pk': self.pk})


class TrainingCategory(models.Model):
    reference_number = models.IntegerField(unique=True)
    name = models.CharField(max_length=50)

    def __str__(self):
        return "{}. {}".format(self.reference_number, self.name)

    class Meta:
        verbose_name_plural = 'Training Categories'


class TrainingItem(models.Model):
    reference_number = models.IntegerField()
    category = models.ForeignKey('TrainingCategory', related_name='items', on_delete=models.RESTRICT)
    name = models.CharField(max_length=50)
    active = models.BooleanField(default=True)

    @property
    def display_id(self):
        return "{}.{}".format(self.category.reference_number, self.reference_number)

    def __str__(self):
        name = "{} {}".format(self.display_id, self.name)
        if not self.active:
            name += " (inactive)"
        return name

    @staticmethod
    def user_has_qualification(item, user, depth):
        return user.qualifications_obtained.only('item', 'depth').filter(item=item, depth__gte=depth).exists()

    class Meta:
        unique_together = ["reference_number", "active", "category"]
        ordering = ['category__reference_number', 'reference_number']


@reversion.register(follow=['trainee'])
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
    depth = models.IntegerField(choices=CHOICES)
    trainee = models.ForeignKey('Trainee', related_name='qualifications_obtained', on_delete=models.RESTRICT)
    date = models.DateField()
    # TODO Remember that some training is external. Support for making an organisation the trainer?
    supervisor = models.ForeignKey('Trainee', related_name='qualifications_granted', on_delete=models.RESTRICT)
    notes = models.TextField(blank=True)
    # TODO Maximum depth - some things stop at Complete and you can't be passed out in them

    def __str__(self):
        return "{} in {} on {}".format(self.get_depth_display(), self.item, self.date.strftime("%b %d %Y"))

    @property
    def activity_feed_string(self):
        return str("{} in {}".format(self.get_depth_display(), self.item))

    @classmethod
    def get_colour_from_depth(obj, depth):
        if depth == 0:
            return "warning"
        elif depth == 1:
            return "success"
        else:
            return "info"

    def get_absolute_url(self):
        return reverse('trainee_item_detail', kwargs={'pk': self.trainee.pk})

    class Meta:
        unique_together = ["trainee", "item", "depth"]
        order_with_respect_to = 'item'


# Levels
@reversion.register(follow=["requirements"])
class TrainingLevel(models.Model, RevisionMixin):
    description = models.TextField(blank=True)
    TA = 0
    TECHNICIAN = 1
    SUPERVISOR = 2
    CHOICES = (
        (TA, 'Technical Assistant'),
        (TECHNICIAN, 'Technician'),
        (SUPERVISOR, 'Supervisor'),
    )
    SOUND = 0
    LIGHTING = 1
    POWER = 2
    RIGGING = 3
    HAULAGE = 4
    DEPARTMENTS = (
        (SOUND, 'Sound'),
        (LIGHTING, 'Lighting'),
        (POWER, 'Power'),
        (RIGGING, 'Rigging'),
        (HAULAGE, 'Haulage'),
    )
    department = models.IntegerField(choices=DEPARTMENTS, null=True, blank=True)  # N.B. Technical Assistant does not have a department
    level = models.IntegerField(choices=CHOICES)
    prerequisite_levels = models.ManyToManyField('self', related_name='prerequisites', symmetrical=False, blank=True)
    icon = models.CharField(null=True, blank=True, max_length=20)

    @property
    def department_colour(self):
        if self.department == self.SOUND:
            return "info"
        elif self.department == self.LIGHTING:
            return "dark"
        elif self.department == self.POWER:
            return "danger"
        elif self.department == self.RIGGING:
            return "warning"
        elif self.department == self.HAULAGE:
            return "light"
        else:
            return "primary"

    def get_requirements_of_depth(self, depth):
        return self.requirements.filter(depth=depth)

    @property
    def is_common_competencies(self):
        return self.department is None and self.level > 0

    @property
    def started_requirements(self):
        return self.get_requirements_of_depth(TrainingItemQualification.STARTED)

    @property
    def complete_requirements(self):
        return self.get_requirements_of_depth(TrainingItemQualification.COMPLETE)

    @property
    def passed_out_requirements(self):
        return self.get_requirements_of_depth(TrainingItemQualification.PASSED_OUT)

    def percentage_complete(self, user):
        needed_qualifications = self.requirements.all().select_related('item')
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
        has_required_items = all(TrainingItem.user_has_qualification(req.item, user, req.depth) for req in self.requirements.all())
        has_required_levels = set(user.level_qualifications.values_list('level', flat=True)).issubset(set(self.prerequisite_levels.all()))
        return has_required_items and has_required_levels

    def __str__(self):
        if self.department is None:
            if self.level == self.TA:
                return self.get_level_display()
            else:
                return "{} Common Competencies".format(self.get_level_display())
        else:
            return "{} {}".format(self.get_department_display(), self.get_level_display())

    @property
    def activity_feed_string(self):
        return str(self)

    def get_absolute_url(self):
        return reverse('level_detail', kwargs={'pk': self.pk})

    @property
    def get_icon(self):
        if self.icon is not None:
            icon = "<span class='fas fa-{}'></span>".format(self.icon)
        else:
            icon = "".join([w[0] for w in str(self).split()])
        return mark_safe("<span class='badge badge-{} badge-pill' data-toggle='tooltip' title='{}'>{}</span>".format(self.department_colour, str(self), icon))


@reversion.register
class TrainingLevelRequirement(models.Model, RevisionMixin):
    level = models.ForeignKey('TrainingLevel', related_name='requirements', on_delete=models.RESTRICT)
    item = models.ForeignKey('TrainingItem', on_delete=models.RESTRICT)
    depth = models.IntegerField(choices=TrainingItemQualification.CHOICES)

    reversion_hide = True

    def __str__(self):
        return "{} in {}".format(TrainingItemQualification.CHOICES[self.depth][1], self.item)

    class Meta:
        unique_together = ["level", "item"]


@reversion.register(follow=['trainee'])
class TrainingLevelQualification(models.Model, RevisionMixin):
    trainee = models.ForeignKey('Trainee', related_name='level_qualifications', on_delete=models.RESTRICT)
    level = models.ForeignKey('TrainingLevel', on_delete=models.RESTRICT)
    confirmed_on = models.DateTimeField(null=True)
    confirmed_by = models.ForeignKey('Trainee', related_name='confirmer', on_delete=models.RESTRICT, null=True)

    reversion_hide = True

    @property
    def get_icon(self):
        return self.level.get_icon

    def __str__(self):
        if self.level.is_common_competencies:
            return "{} is qualified in the {}".format(self.trainee, self.level)
        return "{} is qualified as a {}".format(self.trainee, self.level)

    class Meta:
        unique_together = ["trainee", "level"]
        ordering = ['-confirmed_on']

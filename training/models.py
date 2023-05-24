import datetime
from RIGS.models import Profile, filter_by_pk
from reversion import revisions as reversion
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, F, Value, CharField
from django.db.models.functions import Concat
from django.urls import reverse
from django.utils.safestring import mark_safe
from versioning.versioning import RevisionMixin
from queryable_properties.properties import queryable_property
from queryable_properties.managers import QueryablePropertiesManager
from django.utils.translation import gettext_lazy as _


class TraineeManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True, is_approved=True)

    def search(self, query=None):
        qs = self.get_queryset()
        if query is not None:
            or_lookup = (Q(first_name__icontains=query) |
                         Q(last_name__icontains=query) | Q(initials__icontains=query)
                         )
            or_lookup = filter_by_pk(or_lookup, query)
            qs = qs.filter(or_lookup).distinct()  # distinct() is often necessary with Q lookups
        return qs


@reversion.register(for_concrete_model=False, fields=['is_supervisor'])
class Trainee(Profile, RevisionMixin):
    class Meta:
        proxy = True

    objects = TraineeManager()

    # FIXME use queryset
    def started_levels(self):
        return [level for level in TrainingLevel.objects.all() if level.percentage_complete(self) > 0 and level.pk not in self.level_qualifications.values_list('level', flat=True)]

    @property
    def confirmed_levels(self):
        return self.level_qualifications.exclude(confirmed_on=None).select_related('level')

    @property
    def is_technician(self):
        return self.confirmed_levels \
            .filter(level__level=TrainingLevel.TECHNICIAN) \
            .exclude(level__department=TrainingLevel.HAULAGE) \
            .exclude(level__department__isnull=True).exists()

    @property
    def is_driver(self):
        return self.confirmed_levels.filter(level__department=TrainingLevel.HAULAGE).exists()

    def get_records_of_depth(self, depth):
        return self.qualifications_obtained.filter(depth=depth).select_related('item', 'trainee', 'supervisor')

    def is_user_qualified_in(self, item, required_depth):
        return self.qualifications_obtained.values('item', 'depth').filter(item=item).filter(depth__gte=required_depth).exists()

    def get_absolute_url(self):
        return reverse('trainee_detail', kwargs={'pk': self.pk})

    @property
    def display_id(self):
        return str(self)


class TrainingCategory(models.Model):
    reference_number = models.IntegerField(unique=True)
    name = models.CharField(max_length=50)
    training_level = models.ForeignKey('TrainingLevel', on_delete=models.CASCADE, null=True, help_text="If this is set, any user with the selected level may pass out users within this category, regardless of other status")

    def __str__(self):
        return f"{self.reference_number}. {self.name}"

    class Meta:
        verbose_name_plural = 'Training Categories'
        ordering = ['reference_number']


class TrainingItemManager(QueryablePropertiesManager):
    def search(self, query=None):
        qs = self.get_queryset()
        if query is not None:
            or_lookup = (Q(name__icontains=query) | Q(description__icontains=query) | Q(display_id=query))
            qs = qs.filter(or_lookup).distinct()  # distinct() is often necessary with Q lookups
        return qs


@reversion.register
class TrainingItem(models.Model):
    reference_number = models.IntegerField()
    category = models.ForeignKey('TrainingCategory', related_name='items', on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    active = models.BooleanField(default=True)
    prerequisites = models.ManyToManyField('self', symmetrical=False, blank=True)

    objects = TrainingItemManager()

    @queryable_property
    def display_id(self):
        return f"{self.category.reference_number}.{self.reference_number}"

    @property
    def display_name(self):
        return f"{self.display_id} | {self.name}"

    @display_id.filter
    @classmethod
    def display_id(cls, lookup, value):
        if '.' in str(value):
            try:
                category_number, number = value.split('.', 2)
                if category_number and number:
                    return Q(category__reference_number=int(category_number), reference_number=int(number))
            except ValueError:
                pass
        return models.Q()

    def __str__(self):
        name = f"{self.display_id} {self.name}"
        if not self.active:
            name += " (inactive)"
        return name

    def get_absolute_url(self):
        return reverse('item_list')

    def has_prereqs(self):
        return self.prerequisites.all().exists()

    def user_has_requirements(self, user):
        # Always true if there are no prerequisites, otherwise get a set of prerequsite IDs and check if they are a subset of the set of qualification IDs
        return not self.has_prereqs() or set(self.prerequisites.values_list('pk', flat=True)).issubset(set(user.qualifications_obtained.values_list('item', flat=True)))

    @staticmethod
    def user_has_qualification(item, user, depth):
        return user.qualifications_obtained.only('item', 'depth').filter(item=item, depth__gte=depth).exists()

    class Meta:
        unique_together = ["reference_number", "active", "category"]
        ordering = ['category__reference_number', 'reference_number']


class TrainingItemQualificationManager(QueryablePropertiesManager):
    def search(self, query=None):
        qs = self.get_queryset().select_related('item', 'supervisor', 'item__category')
        if query is not None:
            or_lookup = (Q(item__name__icontains=query) | Q(supervisor__first_name__icontains=query) | Q(supervisor__last_name__icontains=query) | Q(item__category__name__icontains=query) | Q(item__display_id=query))

            try:
                or_lookup = Q(item__category__reference_number=int(query)) | or_lookup
            except:  # noqa
                pass

            qs = qs.filter(or_lookup).distinct()
        return qs


@reversion.register
class TrainingItemQualification(models.Model, RevisionMixin):
    STARTED = 0
    COMPLETE = 1
    PASSED_OUT = 2
    CHOICES = (
        (STARTED, 'Training Started'),
        (COMPLETE, 'Training Complete'),
        (PASSED_OUT, 'Passed Out'),
    )
    item = models.ForeignKey('TrainingItem', on_delete=models.CASCADE)
    depth = models.IntegerField(choices=CHOICES)
    trainee = models.ForeignKey('Trainee', related_name='qualifications_obtained', on_delete=models.CASCADE)
    date = models.DateField()
    # TODO Remember that some training is external. Support for making an organisation the trainer?
    supervisor = models.ForeignKey('Trainee', related_name='qualifications_granted', on_delete=models.CASCADE)
    notes = models.TextField(blank=True)
    # TODO Maximum depth - some things stop at Complete and you can't be passed out in them

    objects = TrainingItemQualificationManager()

    def clean(self):
        errdict = {}
        # Validate supervisor can train in this item
        if hasattr(self, 'supervisor'):  # This will be false if form validation fails
            if self.item.category.training_level:
                if not self.supervisor.level_qualifications.filter(level=self.item.category.training_level):
                    errdict['supervisor'] = ('Selected supervising person is missing requisite training level to train in this department')
            elif not self.supervisor.is_supervisor:
                errdict['supervisor'] = ('Selected supervisor must actually *be* a supervisor...')
        # Item requirements only apply to being passed out
        if self.depth == TrainingItemQualification.PASSED_OUT and not self.item.user_has_requirements(self.trainee):
            errdict['item'] = ('Missing prerequisites')
        if errdict != {}:  # If there was an error when validation
            raise ValidationError(errdict)

    def __str__(self):
        return f"{self.get_depth_display()} in {self.item} on {self.date.strftime('%b %d %Y')}"

    @property
    def activity_feed_string(self):
        return f"{self.trainee} {self.get_depth_display().lower()} in {self.item}"

    @classmethod
    def get_colour_from_depth(cls, depth):
        if depth == 0:
            return "warning"
        if depth == 1:
            return "success"

        return "info"

    def get_absolute_url(self):
        return reverse('edit_qualification', kwargs={'pk': self.pk})

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

    class Meta:
        ordering = ["department", "level"]

    @property
    def department_colour(self):
        if self.department == self.SOUND:
            return "info"
        if self.department == self.LIGHTING:
            return "dark"
        if self.department == self.POWER:
            return "danger"
        if self.department == self.RIGGING:
            return "warning"
        if self.department == self.HAULAGE:
            return "light"

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

        return 0

    def user_has_requirements(self, user):
        has_required_items = all(TrainingItem.user_has_qualification(req.item, user, req.depth) for req in self.requirements.all())
        # Always true if there are no prerequisites, otherwise get a set of prerequsite IDs and check if they are a subset of the set of qualification IDs
        has_required_levels = not self.prerequisite_levels.all().exists() or set(self.prerequisite_levels.values_list('pk', flat=True)).issubset(set(user.level_qualifications.values_list('level', flat=True)))
        return has_required_items and has_required_levels

    def __str__(self):
        if self.department is None:
            if self.level == self.TA:
                return self.get_level_display()
            else:
                return f"{self.get_level_display()} Common Competencies"
        else:
            return f"{self.get_department_display()} {self.get_level_display()}"

    @property
    def activity_feed_string(self):
        return str(self)

    def get_absolute_url(self):
        return reverse('level_detail', kwargs={'pk': self.pk})

    @property
    def get_icon(self):
        if self.icon is not None:
            icon = f"<span class='fas fa-{self.icon}'></span>"
        else:
            icon = "".join([w[0] for w in str(self).split()])
        return mark_safe(f"<span class='badge badge-{self.department_colour} badge-pill' data-toggle='tooltip' title='{str(self)}'>{icon}</span>")


@reversion.register
class TrainingLevelRequirement(models.Model, RevisionMixin):
    level = models.ForeignKey('TrainingLevel', related_name='requirements', on_delete=models.CASCADE)
    item = models.ForeignKey('TrainingItem', on_delete=models.CASCADE)
    depth = models.IntegerField(choices=TrainingItemQualification.CHOICES)

    reversion_hide = True

    def __str__(self):
        depth = TrainingItemQualification.CHOICES[self.depth][1]
        return f"{depth} in {self.item}"

    class Meta:
        unique_together = ["level", "item"]


@reversion.register
class TrainingLevelQualification(models.Model, RevisionMixin):
    trainee = models.ForeignKey('Trainee', related_name='level_qualifications', on_delete=models.CASCADE)
    level = models.ForeignKey('TrainingLevel', on_delete=models.CASCADE)
    confirmed_on = models.DateTimeField(null=True)
    confirmed_by = models.ForeignKey('Trainee', related_name='confirmer', on_delete=models.CASCADE, null=True)

    @property
    def get_icon(self):
        return self.level.get_icon

    def clean(self):
        if self.level.level >= TrainingLevel.SUPERVISOR and self.level.department != TrainingLevel.HAULAGE:
            self.trainee.is_supervisor = True
            self.trainee.save()

    def __str__(self):
        if self.level.is_common_competencies:
            return f"{self.trainee} is qualified in the {self.level}"
        return f"{self.trainee} is qualified as a {self.level}"

    @property
    def activity_feed_string(self):
        return str(self)

    def get_absolute_url(self):
        return reverse('trainee_detail', kwargs={'pk': self.trainee_id})

    class Meta:
        unique_together = ["trainee", "level"]
        ordering = ['-confirmed_on']

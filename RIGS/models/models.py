import hashlib
import random
import string
from collections import Counter

from django.db.models import Q
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse
from versioning.versioning import RevisionMixin
from .events import Event
from .utils import filter_by_pk


class Profile(AbstractUser):
    initials = models.CharField(max_length=5, null=True, blank=False)
    phone = models.CharField(max_length=13, blank=True, default='')
    api_key = models.CharField(max_length=40, blank=True, editable=False, default='')
    is_approved = models.BooleanField(default=False, verbose_name="Approval Status", help_text="Designates whether a staff member has approved this user.")
    # Currently only populated by the admin approval email. TODO: Populate it each time we send any email, might need that...
    last_emailed = models.DateTimeField(blank=True, null=True)
    dark_theme = models.BooleanField(default=False)
    is_supervisor = models.BooleanField(default=False)

    reversion_hide = True

    @classmethod
    def make_api_key(cls):
        size = 20
        chars = string.ascii_letters + string.digits
        new_api_key = ''.join(random.choice(chars) for x in range(size))
        return new_api_key

    @property
    def profile_picture(self):
        url = ""
        if settings.USE_GRAVATAR or settings.USE_GRAVATAR is None:
            url = "https://www.gravatar.com/avatar/" + hashlib.md5(
                self.email.encode('utf-8')).hexdigest() + "?d=wavatar&s=500"
        return url

    @property
    def name(self):
        name = self.get_full_name()
        if self.initials:
            name += f' "{self.initials}"'
        return name

    @property
    def latest_events(self):
        return self.event_mic.order_by('-start_date').select_related('person', 'organisation', 'venue', 'mic', 'riskassessment', 'invoice').prefetch_related('checklists')

    @classmethod
    def admins(cls):
        return Profile.objects.filter(email__in=[y for x in settings.ADMINS for y in x])

    @classmethod
    def users_awaiting_approval_count(cls):
        return Profile.objects.filter(models.Q(is_approved=False)).count()

    def __str__(self):
        return self.name


class ContactableManager(models.Manager):
    def search(self, query=None):
        qs = self.get_queryset()
        if query is not None:
            or_lookup = Q(name__icontains=query) | Q(email__icontains=query) | Q(address__icontains=query) | Q(notes__icontains=query) | Q(
                phone__startswith=query) | Q(phone__endswith=query)

            or_lookup = filter_by_pk(or_lookup, query)

            qs = qs.filter(or_lookup).distinct()  # distinct() is often necessary with Q lookups
        return qs


class Person(models.Model, RevisionMixin):
    name = models.CharField(max_length=50)
    phone = models.CharField(max_length=15, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    address = models.TextField(blank=True, default='')
    notes = models.TextField(blank=True, default='')

    objects = ContactableManager()

    def __str__(self):
        string = self.name
        if self.notes is not None:
            if len(self.notes) > 0:
                string += "*"
        return string

    @property
    def organisations(self):
        o = []
        for e in Event.objects.filter(person=self).select_related('organisation'):
            if e.organisation:
                o.append(e.organisation)

        # Count up occurances and put them in descending order
        c = Counter(o)
        stats = c.most_common()
        return stats

    @property
    def latest_events(self):
        return self.event_set.order_by('-start_date').select_related('person', 'organisation', 'venue', 'mic')

    def get_absolute_url(self):
        return reverse('person_detail', kwargs={'pk': self.pk})


class Organisation(models.Model, RevisionMixin):
    name = models.CharField(max_length=50)
    phone = models.CharField(max_length=15, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    address = models.TextField(blank=True, default='')
    notes = models.TextField(blank=True, default='')
    union_account = models.BooleanField(default=False)

    objects = ContactableManager()

    def __str__(self):
        string = self.name
        if self.notes is not None:
            if len(self.notes) > 0:
                string += "*"
        return string

    @property
    def persons(self):
        p = []
        for e in Event.objects.filter(organisation=self).select_related('person'):
            if e.person:
                p.append(e.person)

        # Count up occurances and put them in descending order
        c = Counter(p)
        stats = c.most_common()
        return stats

    @property
    def latest_events(self):
        return self.event_set.order_by('-start_date').select_related('person', 'organisation', 'venue', 'mic')

    def get_absolute_url(self):
        return reverse('organisation_detail', kwargs={'pk': self.pk})


class Venue(models.Model, RevisionMixin):
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=15, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    three_phase_available = models.BooleanField(default=False)
    notes = models.TextField(blank=True, default='')
    address = models.TextField(blank=True, default='')

    objects = ContactableManager()

    def __str__(self):
        string = self.name
        if self.notes and len(self.notes) > 0:
            string += "*"
        return string

    @property
    def latest_events(self):
        return self.event_set.order_by('-start_date').select_related('person', 'organisation', 'venue', 'mic')

    def get_absolute_url(self):
        return reverse('venue_detail', kwargs={'pk': self.pk})

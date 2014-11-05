from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
import hashlib
import reversion

# Create your models here.
class Profile(AbstractUser):
    initials = models.CharField(max_length=5, unique=True, null=True, blank=True)
    phone = models.CharField(max_length=13, null=True, blank=True)

    @property
    def profile_picture(self):
        url = ""
        if settings.USE_GRAVATAR or settings.USE_GRAVATAR is None:
            url = "https://www.gravatar.com/avatar/" + hashlib.md5(self.email).hexdigest() + "?d=identicon&s=500"
        return url


class RevisionMixin(object):
    @property
    def last_edited_at(self):
        version = reversion.get_for_object(self)[0]
        return version.revision.date_created

    @property
    def last_edited_by(self):
        version = reversion.get_for_object(self)[0]
        return version.revision.user


@reversion.register
class Person(models.Model, RevisionMixin):
    name = models.CharField(max_length=50)
    phone = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)

    address = models.TextField(blank=True, null=True)

    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        string = self.name
        if len(self.notes) > 0:
            string += "*"
        return string


@reversion.register
class Organisation(models.Model, RevisionMixin):
    name = models.CharField(max_length=50)
    phone = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)

    address = models.TextField(blank=True, null=True)

    notes = models.TextField(blank=True, null=True)
    union_account = models.BooleanField(default=False)

    def __str__(self):
        string = self.name
        if len(self.notes) > 0:
            string += "*"
        return string


@reversion.register
class VatRate(models.Model, RevisionMixin):
    start_at = models.DateTimeField()
    rate = models.DecimalField(max_digits=6, decimal_places=6)
    comment = models.CharField(max_length=255)

    @property
    def as_percent(self):
        return (self.rate * 100)

    def __str__(self):
        return self.comment + " " + str(self.start_at) + " @ " + str(self.as_percent) + "%"


@reversion.register
class Venue(models.Model, RevisionMixin):
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    three_phase_available = models.BooleanField(default=False)
    notes = models.TextField(blank=True, null=True)

    address = models.TextField(blank=True, null=True)

    def __str__(self):
        string = self.name
        if self.notes and len(self.notes) > 0:
           string += "*"
        return string


@reversion.register(follow=['items'])
class Event(models.Model, RevisionMixin):
    # Done to make it much nicer on the database
    PROVISIONAL = 0
    CONFIRMED = 1
    BOOKED = 2
    CANCELLED = 3
    EVENT_STATUS_CHOICES = (
        (PROVISIONAL, 'Provisional'),
        (CONFIRMED, 'Confirmed'),
        (BOOKED, 'Booked'),
        (CANCELLED, 'Cancelled'),
    )

    name = models.CharField(max_length=255)
    person = models.ForeignKey('Person')
    organisation = models.ForeignKey('Organisation', blank=True, null=True)
    venue = models.ForeignKey('Venue')
    description = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    status = models.IntegerField(choices=EVENT_STATUS_CHOICES, default=PROVISIONAL)
    dry_hire = models.BooleanField(default=False)
    is_rig = models.BooleanField(default=True)
    based_on = models.ForeignKey('Event', related_name='future_events', blank=True, null=True)

    # Timing
    start_date = models.DateField()
    start_time = models.TimeField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    end_time = models.TimeField(blank=True, null=True)
    access_at = models.DateTimeField(blank=True, null=True)
    meet_at = models.DateTimeField(blank=True, null=True)
    meet_info = models.CharField(max_length=255, blank=True, null=True)

    # Crew management
    checked_in_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='event_checked_in', blank=True, null=True)
    mic = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='event_mic', blank=True, null=True)

    # Monies
    payment_method = models.CharField(max_length=255, blank=True, null=True)
    payment_received = models.CharField(max_length=255, blank=True, null=True)
    purchase_order = models.CharField(max_length=255, blank=True, null=True)
    collector = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return str(self.pk) + ": " + self.name


class EventItem(models.Model):
    event = models.ForeignKey('Event', related_name='items')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    quantity = models.IntegerField()
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    order = models.IntegerField()

    @property
    def total_cost(self):
        return self.cost * self.quantity

    def __str__(self):
        return self.event.name + " | " + self.name


class EventCrew(models.Model):
    event = models.ForeignKey('Event', related_name='crew')
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    rig = models.BooleanField(default=False)
    run = models.BooleanField(default=False)
    derig = models.BooleanField(default=False)
    notes = models.TextField(blank=True, null=True)

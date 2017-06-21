import datetime
import hashlib
import datetime, pytz

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.encoding import python_2_unicode_compatible
from reversion import revisions as reversion
from reversion.models import Version
import string

import random
from collections import Counter
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse_lazy


# Create your models here.
@python_2_unicode_compatible
class Profile(AbstractUser):
    initials = models.CharField(max_length=5, unique=True, null=True, blank=False)
    phone = models.CharField(max_length=13, null=True, blank=True)
    api_key = models.CharField(max_length=40, blank=True, editable=False, null=True)

    @classmethod
    def make_api_key(cls):
        size = 20
        chars = string.ascii_letters + string.digits
        new_api_key = ''.join(random.choice(chars) for x in range(size))
        return new_api_key;

    @property
    def profile_picture(self):
        url = ""
        if settings.USE_GRAVATAR or settings.USE_GRAVATAR is None:
            url = "https://www.gravatar.com/avatar/" + hashlib.md5(self.email).hexdigest() + "?d=wavatar&s=500"
        return url

    @property
    def name(self):
        name = self.get_full_name()
        if self.initials:
            name += ' "{}"'.format(self.initials)
        return name

    @property
    def latest_events(self):
        return self.event_mic.order_by('-start_date').select_related('person', 'organisation', 'venue', 'mic')

    def __str__(self):
        return self.name

    class Meta:
        permissions = (
            ('view_profile', 'Can view Profile'),
        )


class RevisionMixin(object):
    @property
    def current_version(self):
        version = Version.objects.get_for_object(self).select_related('revision').first()
        return version

    @property
    def last_edited_at(self):
        version = self.current_version
        if version is None:
            return None
        return version.revision.date_created

    @property
    def last_edited_by(self):
        version = self.current_version
        if version is None:
            return None
        return version.revision.user

    @property
    def current_version_id(self):
        version = self.current_version
        if version is None:
            return None
        return "V{0} | R{1}".format(version.pk, version.revision.pk)


@reversion.register
@python_2_unicode_compatible
class Person(models.Model, RevisionMixin):
    name = models.CharField(max_length=50)
    phone = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)

    address = models.TextField(blank=True, null=True)

    notes = models.TextField(blank=True, null=True)

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
        return reverse_lazy('person_detail', kwargs={'pk': self.pk})

    class Meta:
        permissions = (
            ('view_person', 'Can view Persons'),
        )


@reversion.register
@python_2_unicode_compatible
class Organisation(models.Model, RevisionMixin):
    name = models.CharField(max_length=50)
    phone = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)

    address = models.TextField(blank=True, null=True)

    notes = models.TextField(blank=True, null=True)
    union_account = models.BooleanField(default=False)

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
        return reverse_lazy('organisation_detail', kwargs={'pk': self.pk})

    class Meta:
        permissions = (
            ('view_organisation', 'Can view Organisations'),
        )


class VatManager(models.Manager):
    def current_rate(self):
        return self.find_rate(timezone.now())

    def find_rate(self, date):
        # return self.filter(startAt__lte=date).latest()
        try:
            return self.filter(start_at__lte=date).latest()
        except VatRate.DoesNotExist:
            r = VatRate
            r.rate = 0
            return r


@reversion.register
@python_2_unicode_compatible
class VatRate(models.Model, RevisionMixin):
    start_at = models.DateField()
    rate = models.DecimalField(max_digits=6, decimal_places=6)
    comment = models.CharField(max_length=255)

    objects = VatManager()

    @property
    def as_percent(self):
        return self.rate * 100

    class Meta:
        ordering = ['-start_at']
        get_latest_by = 'start_at'

    def __str__(self):
        return self.comment + " " + str(self.start_at) + " @ " + str(self.as_percent) + "%"


@reversion.register
@python_2_unicode_compatible
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

    @property
    def latest_events(self):
        return self.event_set.order_by('-start_date').select_related('person', 'organisation', 'venue', 'mic')

    def get_absolute_url(self):
        return reverse_lazy('venue_detail', kwargs={'pk': self.pk})

    class Meta:
        permissions = (
            ('view_venue', 'Can view Venues'),
        )


class EventManager(models.Manager):
    def current_events(self):
        events = self.filter(
            (models.Q(start_date__gte=timezone.now().date(), end_date__isnull=True, dry_hire=False) & ~models.Q(status=Event.CANCELLED)) |  # Starts after with no end
            (models.Q(end_date__gte=timezone.now().date(), dry_hire=False) & ~models.Q(status=Event.CANCELLED)) |  # Ends after
            (models.Q(dry_hire=True, start_date__gte=timezone.now().date()) & ~models.Q(status=Event.CANCELLED)) |  # Active dry hire
            (models.Q(dry_hire=True, checked_in_by__isnull=True) & (models.Q(status=Event.BOOKED) | models.Q(status=Event.CONFIRMED))) |  # Active dry hire GT
            models.Q(status=Event.CANCELLED, start_date__gte=timezone.now().date())  # Canceled but not started
        ).order_by('start_date', 'end_date', 'start_time', 'end_time', 'meet_at').select_related('person', 'organisation', 'venue', 'mic')
        return events

    def events_in_bounds(self, start, end):
        events = self.filter(
            (models.Q(start_date__gte=start.date(), start_date__lte=end.date())) |  # Start date in bounds
            (models.Q(end_date__gte=start.date(), end_date__lte=end.date())) |  # End date in bounds
            (models.Q(access_at__gte=start, access_at__lte=end)) |  # Access at in bounds
            (models.Q(meet_at__gte=start, meet_at__lte=end)) |  # Meet at in bounds

            (models.Q(start_date__lte=start, end_date__gte=end)) |  # Start before, end after
            (models.Q(access_at__lte=start, start_date__gte=end)) |  # Access before, start after
            (models.Q(access_at__lte=start, end_date__gte=end)) |  # Access before, end after
            (models.Q(meet_at__lte=start, start_date__gte=end)) |  # Meet before, start after
            (models.Q(meet_at__lte=start, end_date__gte=end))  # Meet before, end after

        ).order_by('start_date', 'end_date', 'start_time', 'end_time', 'meet_at').select_related('person',
                                                                                                 'organisation',
                                                                                                 'venue', 'mic')
        return events

    def rig_count(self):
        event_count = self.filter(
            (models.Q(start_date__gte=timezone.now().date(), end_date__isnull=True, dry_hire=False,
                      is_rig=True) & ~models.Q(
                status=Event.CANCELLED)) |  # Starts after with no end
            (models.Q(end_date__gte=timezone.now().date(), dry_hire=False, is_rig=True) & ~models.Q(
                status=Event.CANCELLED)) |  # Ends after
            (models.Q(dry_hire=True, start_date__gte=timezone.now().date(), is_rig=True) & ~models.Q(
                status=Event.CANCELLED)) |  # Active dry hire
            (models.Q(dry_hire=True, checked_in_by__isnull=True, is_rig=True) & (
                models.Q(status=Event.BOOKED) | models.Q(status=Event.CONFIRMED)))  # Active dry hire GT
        ).count()
        return event_count


@reversion.register(follow=['items'])
@python_2_unicode_compatible
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
    person = models.ForeignKey('Person', null=True, blank=True)
    organisation = models.ForeignKey('Organisation', blank=True, null=True)
    venue = models.ForeignKey('Venue', blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    status = models.IntegerField(choices=EVENT_STATUS_CHOICES, default=PROVISIONAL)
    dry_hire = models.BooleanField(default=False)
    is_rig = models.BooleanField(default=True)
    based_on = models.ForeignKey('Event', on_delete=models.SET_NULL, related_name='future_events', blank=True,
                                 null=True)

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
    mic = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='event_mic', blank=True, null=True,
                            verbose_name="MIC")

    # Monies
    payment_method = models.CharField(max_length=255, blank=True, null=True)
    payment_received = models.CharField(max_length=255, blank=True, null=True)
    purchase_order = models.CharField(max_length=255, blank=True, null=True, verbose_name='PO')
    collector = models.CharField(max_length=255, blank=True, null=True, verbose_name='collected by')

    # Authorisation request details
    auth_request_by = models.ForeignKey('Profile', null=True, blank=True)
    auth_request_at = models.DateTimeField(null=True, blank=True)
    auth_request_to = models.EmailField(null=True, blank=True)

    # Calculated values
    """
    EX Vat
    """

    @property
    def sum_total(self):
        # Manual querying is required for efficiency whilst maintaining floating point arithmetic
        # if connection.vendor == 'postgresql':
        #    sql = "SELECT SUM(quantity * cost) AS sum_total FROM \"RIGS_eventitem\" WHERE event_id=%i" % self.id
        # else:
        #    sql = "SELECT id, SUM(quantity * cost) AS sum_total FROM RIGS_eventitem WHERE event_id=%i" % self.id
        # total = self.items.raw(sql)[0]
        # if total.sum_total:
        #    return total.sum_total
        # total = 0.0
        # for item in self.items.filter(cost__gt=0).extra(select="SUM(cost * quantity) AS sum"):
        #    total += item.sum
        total = EventItem.objects.filter(event=self).aggregate(
            sum_total=models.Sum(models.F('cost') * models.F('quantity'),
                                 output_field=models.DecimalField(max_digits=10, decimal_places=2))
        )['sum_total']
        if total:
            return total
        return Decimal("0.00")

    @cached_property
    def vat_rate(self):
        return VatRate.objects.find_rate(self.start_date)

    @property
    def vat(self):
        return Decimal(self.sum_total * self.vat_rate.rate).quantize(Decimal('.01'))

    """
    Inc VAT
    """

    @property
    def total(self):
        return Decimal(self.sum_total + self.vat).quantize(Decimal('.01'))

    @property
    def cancelled(self):
        return (self.status == self.CANCELLED)

    @property
    def confirmed(self):
        return (self.status == self.BOOKED or self.status == self.CONFIRMED)

    @property
    def authorised(self):
        return not self.internal and self.purchase_order or self.authorisation.amount == self.total

    @property
    def has_start_time(self):
        return self.start_time is not None

    @property
    def has_end_time(self):
        return self.end_time is not None

    @property
    def earliest_time(self):
        """Finds the earliest time defined in the event - this function could return either a tzaware datetime, or a naiive date object"""

        # Put all the datetimes in a list
        datetime_list = []

        if self.access_at:
            datetime_list.append(self.access_at)

        if self.meet_at:
            datetime_list.append(self.meet_at)

        # If there is no start time defined, pretend it's midnight
        startTimeFaked = False
        if self.has_start_time:
            startDateTime = datetime.datetime.combine(self.start_date, self.start_time)
        else:
            startDateTime = datetime.datetime.combine(self.start_date, datetime.time(00, 00))
            startTimeFaked = True

        # timezoneIssues - apply the default timezone to the naiive datetime
        tz = pytz.timezone(settings.TIME_ZONE)
        startDateTime = tz.localize(startDateTime)
        datetime_list.append(startDateTime)  # then add it to the list

        earliest = min(datetime_list).astimezone(tz)  # find the earliest datetime in the list

        # if we faked it & it's the earliest, better own up
        if startTimeFaked and earliest == startDateTime:
            return self.start_date

        return earliest

    @property
    def latest_time(self):
        """Returns the end of the event - this function could return either a tzaware datetime, or a naiive date object"""
        tz = pytz.timezone(settings.TIME_ZONE)
        endDate = self.end_date
        if endDate is None:
            endDate = self.start_date

        if self.has_end_time:
            endDateTime = datetime.datetime.combine(endDate, self.end_time)
            tz = pytz.timezone(settings.TIME_ZONE)
            endDateTime = tz.localize(endDateTime)

            return endDateTime

        else:
            return endDate

    @property
    def internal(self):
        return self.organisation and self.organisation.union_account

    objects = EventManager()

    def get_absolute_url(self):
        return reverse_lazy('event_detail', kwargs={'pk': self.pk})

    def __str__(self):
        return str(self.pk) + ": " + self.name

    def clean(self):
        if self.end_date and self.start_date > self.end_date:
            raise ValidationError('Unless you\'ve invented time travel, the event can\'t finish before it has started.')

        startEndSameDay = not self.end_date or self.end_date == self.start_date
        hasStartAndEnd = self.has_start_time and self.has_end_time
        if startEndSameDay and hasStartAndEnd and self.start_time > self.end_time:
            raise ValidationError('Unless you\'ve invented time travel, the event can\'t finish before it has started.')

    def save(self, *args, **kwargs):
        """Call :meth:`full_clean` before saving."""
        self.full_clean()
        super(Event, self).save(*args, **kwargs)

    class Meta:
        permissions = (
            ('view_event', 'Can view Events'),
        )


class EventItem(models.Model):
    event = models.ForeignKey('Event', related_name='items', blank=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    quantity = models.IntegerField()
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    order = models.IntegerField()

    @property
    def total_cost(self):
        return self.cost * self.quantity

    class Meta:
        ordering = ['order']

    def __str__(self):
        return str(self.event.pk) + "." + str(self.order) + ": " + self.event.name + " | " + self.name


class EventCrew(models.Model):
    event = models.ForeignKey('Event', related_name='crew')
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    rig = models.BooleanField(default=False)
    run = models.BooleanField(default=False)
    derig = models.BooleanField(default=False)
    notes = models.TextField(blank=True, null=True)


@reversion.register
class EventAuthorisation(models.Model, RevisionMixin):
    event = models.OneToOneField('Event', related_name='authorisation')
    email = models.EmailField()
    name = models.CharField(max_length=255)
    uni_id = models.CharField(max_length=10, blank=True, null=True, verbose_name="University ID")
    account_code = models.CharField(max_length=50, blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="authorisation amount")
    sent_by = models.ForeignKey('RIGS.Profile')

    def get_absolute_url(self):
        return reverse_lazy('event_detail', kwargs={'pk': self.event.pk})

    @property
    def activity_feed_string(self):
        return str("N%05d" % self.event.pk + ' (requested by ' + self.sent_by.initials + ')')


@python_2_unicode_compatible
class Invoice(models.Model):
    event = models.OneToOneField('Event')
    invoice_date = models.DateField(auto_now_add=True)
    void = models.BooleanField(default=False)

    @property
    def sum_total(self):
        return self.event.sum_total

    @property
    def total(self):
        return self.event.total

    @property
    def payment_total(self):
        total = self.payment_set.aggregate(total=models.Sum('amount'))['total']
        if total:
            return total
        return Decimal("0.00")

    @property
    def balance(self):
        return self.sum_total - self.payment_total

    @property
    def is_closed(self):
        return self.balance == 0 or self.void

    def __str__(self):
        return "%i: %s (%.2f)" % (self.pk, self.event, self.balance)

    class Meta:
        permissions = (
            ('view_invoice', 'Can view Invoices'),
        )
        ordering = ['-invoice_date']


@python_2_unicode_compatible
class Payment(models.Model):
    CASH = 'C'
    INTERNAL = 'I'
    EXTERNAL = 'E'
    SUCORE = 'SU'
    ADJUSTMENT = 'T'
    METHODS = (
        (CASH, 'Cash'),
        (INTERNAL, 'Internal'),
        (EXTERNAL, 'External'),
        (SUCORE, 'SU Core'),
        (ADJUSTMENT, 'TEC Adjustment'),
    )

    invoice = models.ForeignKey('Invoice')
    date = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2, help_text='Please use ex. VAT')
    method = models.CharField(max_length=2, choices=METHODS, null=True, blank=True)

    def __str__(self):
        return "%s: %d" % (self.get_method_display(), self.amount)

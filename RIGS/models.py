import datetime
import hashlib
import random
import string
from collections import Counter
from decimal import Decimal
from urllib.parse import urlparse

import pytz
from django import forms
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.functional import cached_property
from reversion import revisions as reversion
from reversion.models import Version


class Profile(AbstractUser):
    initials = models.CharField(max_length=5, unique=True, null=True, blank=False)
    phone = models.CharField(max_length=13, null=True, blank=True)
    api_key = models.CharField(max_length=40, blank=True, editable=False, null=True)
    is_approved = models.BooleanField(default=False)
    last_emailed = models.DateTimeField(blank=True,
                                        null=True)  # Currently only populated by the admin approval email. TODO: Populate it each time we send any email, might need that...

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
            name += ' "{}"'.format(self.initials)
        return name

    @property
    def latest_events(self):
        return self.event_mic.order_by('-start_date').select_related('person', 'organisation', 'venue', 'mic')

    @classmethod
    def admins(cls):
        return Profile.objects.filter(email__in=[y for x in settings.ADMINS for y in x])

    @classmethod
    def users_awaiting_approval_count(cls):
        return Profile.objects.filter(models.Q(is_approved=False)).count()

    def __str__(self):
        return self.name

# TODO move to versioning - currently get import errors with that


class RevisionMixin(object):
    @property
    def is_first_version(self):
        versions = Version.objects.get_for_object(self)
        return len(versions) == 1

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
class VatRate(models.Model, RevisionMixin):
    start_at = models.DateField()
    rate = models.DecimalField(max_digits=6, decimal_places=6)
    comment = models.CharField(max_length=255)

    objects = VatManager()

    reversion_hide = True

    @property
    def as_percent(self):
        return self.rate * 100

    class Meta:
        ordering = ['-start_at']
        get_latest_by = 'start_at'

    def __str__(self):
        return self.comment + " " + str(self.start_at) + " @ " + str(self.as_percent) + "%"


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


class EventManager(models.Manager):
    def current_events(self):
        events = self.filter(
            (models.Q(start_date__gte=timezone.now().date(), end_date__isnull=True, dry_hire=False) & ~models.Q(
                status=Event.CANCELLED)) |  # Starts after with no end
            (models.Q(end_date__gte=timezone.now().date(), dry_hire=False) & ~models.Q(
                status=Event.CANCELLED)) |  # Ends after
            (models.Q(dry_hire=True, start_date__gte=timezone.now().date()) & ~models.Q(
                status=Event.CANCELLED)) |  # Active dry hire
            (models.Q(dry_hire=True, checked_in_by__isnull=True) & (
                models.Q(status=Event.BOOKED) | models.Q(status=Event.CONFIRMED))) |  # Active dry hire GT
            models.Q(status=Event.CANCELLED, start_date__gte=timezone.now().date())  # Canceled but not started
        ).order_by('start_date', 'end_date', 'start_time', 'end_time', 'meet_at').select_related('person',
                                                                                                 'organisation',
                                                                                                 'venue', 'mic')
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
                status=Event.CANCELLED))  # Active dry hire
        ).count()
        return event_count


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
    person = models.ForeignKey('Person', null=True, blank=True, on_delete=models.CASCADE)
    organisation = models.ForeignKey('Organisation', blank=True, null=True, on_delete=models.CASCADE)
    venue = models.ForeignKey('Venue', blank=True, null=True, on_delete=models.CASCADE)
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
    checked_in_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='event_checked_in', blank=True, null=True,
                                      on_delete=models.CASCADE)
    mic = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='event_mic', blank=True, null=True,
                            verbose_name="MIC", on_delete=models.CASCADE)

    # Monies
    payment_method = models.CharField(max_length=255, blank=True, null=True)
    payment_received = models.CharField(max_length=255, blank=True, null=True)
    purchase_order = models.CharField(max_length=255, blank=True, null=True, verbose_name='PO')
    collector = models.CharField(max_length=255, blank=True, null=True, verbose_name='collected by')

    # Authorisation request details
    auth_request_by = models.ForeignKey('Profile', null=True, blank=True, on_delete=models.CASCADE)
    auth_request_at = models.DateTimeField(null=True, blank=True)
    auth_request_to = models.EmailField(null=True, blank=True)

    @property
    def display_id(self):
        if self.is_rig:
            return str("N%05d" % self.pk)
        else:
            return self.pk

    # Calculated values
    """
    EX Vat
    """

    @property
    def sum_total(self):
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
    def hs_done(self):
        return self.riskassessment is not None and len(self.checklists.all()) > 0

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
        return bool(self.organisation and self.organisation.union_account)

    @property
    def authorised(self):
        if self.internal:
            return self.authorisation.amount == self.total
        else:
            return bool(self.purchase_order)

    objects = EventManager()

    def get_absolute_url(self):
        return reverse_lazy('event_detail', kwargs={'pk': self.pk})

    def __str__(self):
        return "{}: {}".format(self.display_id, self.name)

    def clean(self):
        errdict = {}
        if self.end_date and self.start_date > self.end_date:
            errdict['end_date'] = ['Unless you\'ve invented time travel, the event can\'t finish before it has started.']

        startEndSameDay = not self.end_date or self.end_date == self.start_date
        hasStartAndEnd = self.has_start_time and self.has_end_time
        if startEndSameDay and hasStartAndEnd and self.start_time > self.end_time:
            errdict['end_time'] = ['Unless you\'ve invented time travel, the event can\'t finish before it has started.']

        if self.access_at is not None:
            if self.access_at.date() > self.start_date:
                errdict['access_at'] = ['Regardless of what some clients might think, access time cannot be after the event has started.']
            elif self.start_time is not None and self.start_date == self.access_at.date() and self.access_at.time() > self.start_time:
                errdict['access_at'] = ['Regardless of what some clients might think, access time cannot be after the event has started.']

        if errdict != {}:  # If there was an error when validation
            raise ValidationError(errdict)

    def save(self, *args, **kwargs):
        """Call :meth:`full_clean` before saving."""
        self.full_clean()
        super(Event, self).save(*args, **kwargs)


@reversion.register
class EventItem(models.Model, RevisionMixin):
    event = models.ForeignKey('Event', related_name='items', blank=True, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    quantity = models.IntegerField()
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    order = models.IntegerField()

    reversion_hide = True

    @property
    def total_cost(self):
        return self.cost * self.quantity

    class Meta:
        ordering = ['order']

    def __str__(self):
        return str(self.event.pk) + "." + str(self.order) + ": " + self.event.name + " | " + self.name

    @property
    def activity_feed_string(self):
        return str("item {}".format(self.name))


@reversion.register
class EventAuthorisation(models.Model, RevisionMixin):
    event = models.OneToOneField('Event', related_name='authorisation', on_delete=models.CASCADE)
    email = models.EmailField()
    name = models.CharField(max_length=255)
    uni_id = models.CharField(max_length=10, blank=True, null=True, verbose_name="University ID")
    account_code = models.CharField(max_length=50, blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="authorisation amount")
    sent_by = models.ForeignKey('Profile', on_delete=models.CASCADE)

    def get_absolute_url(self):
        return reverse_lazy('event_detail', kwargs={'pk': self.event.pk})

    @property
    def activity_feed_string(self):
        return "{} (requested by {})".format(self.event.display_id, self.sent_by.initials)


@reversion.register(follow=['payment_set'])
class Invoice(models.Model, RevisionMixin):
    event = models.OneToOneField('Event', on_delete=models.CASCADE)
    invoice_date = models.DateField(auto_now_add=True)
    void = models.BooleanField(default=False)

    reversion_perm = 'RIGS.view_invoice'

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

    def get_absolute_url(self):
        return reverse_lazy('invoice_detail', kwargs={'pk': self.pk})

    @property
    def activity_feed_string(self):
        return "#{} for Event {}".format(self.display_id, "N%05d" % self.event.pk)

    def __str__(self):
        return "%i: %s (%.2f)" % (self.pk, self.event, self.balance)

    @property
    def display_id(self):
        return "{:05d}".format(self.pk)

    class Meta:
        ordering = ['-invoice_date']


@reversion.register
class Payment(models.Model, RevisionMixin):
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

    invoice = models.ForeignKey('Invoice', on_delete=models.CASCADE)
    date = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2, help_text='Please use ex. VAT')
    method = models.CharField(max_length=2, choices=METHODS, null=True, blank=True)

    reversion_hide = True

    def __str__(self):
        return "%s: %d" % (self.get_method_display(), self.amount)

    @property
    def activity_feed_string(self):
        return str("payment of £{}".format(self.amount))


def validate_url(value):
    if not value:
        return  # Required error is done the field
    obj = urlparse(value)
    if obj.hostname not in ('nottinghamtec.sharepoint.com'):
        raise ValidationError('URL must point to a location on the TEC Sharepoint')


@reversion.register
class RiskAssessment(models.Model, RevisionMixin):
    SMALL = (0, 'Small')
    MEDIUM = (1, 'Medium')
    LARGE = (2, 'Large')
    SIZES = (SMALL, MEDIUM, LARGE)

    event = models.OneToOneField('Event', on_delete=models.CASCADE)
    # General
    nonstandard_equipment = models.BooleanField(help_text="Does the event require any hired in equipment or use of equipment that is not covered by <a href='https://nottinghamtec.sharepoint.com/:f:/g/HealthAndSafety/Eo4xED_DrqFFsfYIjKzMZIIB6Gm_ZfR-a8l84RnzxtBjrA?e=Bf0Haw'>"
                                                          "TEC's standard risk assessments and method statements?</a>")
    nonstandard_use = models.BooleanField(help_text="Are TEC using their equipment in a way that is abnormal?<br><small>i.e. Not covered by TECs standard health and safety documentation</small>")
    contractors = models.BooleanField(help_text="Are you using any external contractors?<br><small>i.e. Freelancers/Crewing Companies</small>")
    other_companies = models.BooleanField(help_text="Are TEC working with any other companies on site?<br><small>e.g. TEC is providing the lighting while another company does sound</small>")
    crew_fatigue = models.BooleanField(help_text="Is crew fatigue likely to be a risk at any point during this event?")
    general_notes = models.TextField(blank=True, null=True, help_text="Did you have to consult a supervisor about any of the above? If so who did you consult and what was the outcome?")

    # Power
    # event_size = models.IntegerField(blank=True, null=True, choices=SIZES)
    big_power = models.BooleanField(help_text="Does the event require larger power supplies than 13A or 16A single phase wall sockets, or draw more than 20A total current?")
    # If yes to the above two, you must answer...
    power_mic = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='power_mic', blank=True, null=True,
                                  verbose_name="Power MIC", on_delete=models.CASCADE, help_text="Who is the Power MIC? (if yes to the above question, this person <em>must</em> be a Power Technician or Power Supervisor)")
    outside = models.BooleanField(help_text="Is the event outdoors?")
    generators = models.BooleanField(help_text="Will generators be used?")
    other_companies_power = models.BooleanField(help_text="Will TEC be supplying power to any other companies?")
    nonstandard_equipment_power = models.BooleanField(help_text="Does the power plan require the use of any power equipment (distros, dimmers, motor controllers, etc.) that does not belong to TEC?")
    multiple_electrical_environments = models.BooleanField(help_text="Will the electrical installation occupy more than one electrical environment?")
    power_notes = models.TextField(blank=True, null=True, help_text="Did you have to consult a supervisor about any of the above? If so who did you consult and what was the outcome?")
    power_plan = models.URLField(blank=True, null=True, help_text="Upload your power plan to the <a href='https://nottinghamtec.sharepoint.com/'>Sharepoint</a> and submit a link", validators=[validate_url])

    # Sound
    noise_monitoring = models.BooleanField(help_text="Does the event require noise monitoring or any non-standard procedures in order to comply with health and safety legislation or site rules?")
    sound_notes = models.TextField(blank=True, null=True, help_text="Did you have to consult a supervisor about any of the above? If so who did you consult and what was the outcome?")

    # Site
    known_venue = models.BooleanField(help_text="Is this venue new to you (the MIC) or new to TEC?")
    safe_loading = models.BooleanField(help_text="Are there any issues preventing a safe load in or out? (e.g. sufficient lighting, flat, not in a crowded area etc.)")
    safe_storage = models.BooleanField(help_text="Are there any problems with safe and secure equipment storage?")
    area_outside_of_control = models.BooleanField(help_text="Is any part of the work area out of TEC's direct control or openly accessible during the build or breakdown period?")
    barrier_required = models.BooleanField(help_text="Is there a requirement for TEC to provide any barrier for security or protection of persons/equipment?")
    nonstandard_emergency_procedure = models.BooleanField(help_text="Does the emergency procedure for the event differ from TEC's standard procedures?")

    # Structures
    special_structures = models.BooleanField(help_text="Does the event require use of winch stands, motors, MPT Towers, or staging?")
    suspended_structures = models.BooleanField(help_text="Are any structures (excluding projector screens and IWBs) being suspended from TEC's structures?")
    persons_responsible_structures = models.TextField(blank=True, null=True, help_text="Who are the persons on site responsible for their use?")
    rigging_plan = models.URLField(blank=True, null=True, help_text="Upload your rigging plan to the <a href='https://nottinghamtec.sharepoint.com/'>Sharepoint</a> and submit a link", validators=[validate_url])

    # Blimey that was a lot of options

    reviewed_at = models.DateTimeField(null=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True,
                                    verbose_name="Reviewer", on_delete=models.CASCADE)

    supervisor_consulted = models.BooleanField(null=True)

    expected_values = {
        'nonstandard_equipment': False,
        'nonstandard_use': False,
        'contractors': False,
        'other_companies': False,
        'crew_fatigue': False,
        'big_power': False,
        'generators': False,
        'other_companies_power': False,
        'nonstandard_equipment_power': False,
        'multiple_electrical_environments': False,
        'noise_monitoring': False,
        'known_venue': False,
        'safe_loading': False,
        'safe_storage': False,
        'area_outside_of_control': False,
        'barrier_required': False,
        'nonstandard_emergency_procedure': False,
        'special_structures': False,
        'suspended_structures': False,
    }
    inverted_fields = {key: value for (key, value) in expected_values.items() if not value}.keys()

    def clean(self):
        # Check for idiots
        if not self.outside and self.generators:
            raise forms.ValidationError("Engage brain, please. <strong>No generators indoors!(!)</strong>")

    class Meta:
        ordering = ['event']
        permissions = [
            ('review_riskassessment', 'Can review Risk Assessments')
        ]

    @property
    def event_size(self):
        # Confirm event size. Check all except generators, since generators entails outside
        if self.outside or self.other_companies_power or self.nonstandard_equipment_power or self.multiple_electrical_environments:
            return self.LARGE[0]
        elif self.big_power:
            return self.MEDIUM[0]
        else:
            return self.SMALL[0]

    @property
    def activity_feed_string(self):
        return str(self.event)

    def get_absolute_url(self):
        return reverse_lazy('ra_detail', kwargs={'pk': self.pk})

    def __str__(self):
        return "%i - %s" % (self.pk, self.event)


@reversion.register(follow=['vehicles', 'crew'])
class EventChecklist(models.Model, RevisionMixin):
    event = models.ForeignKey('Event', related_name='checklists', on_delete=models.CASCADE)

    # General
    power_mic = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True, related_name='checklists',
                                  verbose_name="Power MIC", on_delete=models.CASCADE, help_text="Who is the Power MIC?")
    venue = models.ForeignKey('Venue', on_delete=models.CASCADE)
    date = models.DateField()

    # Safety Checks
    safe_parking = models.BooleanField(blank=True, null=True, help_text="Vehicles parked safely?<br><small>(does not obstruct venue access)</small>")
    safe_packing = models.BooleanField(blank=True, null=True, help_text="Equipment packed away safely?<br><small>(including flightcases)</small>")
    exits = models.BooleanField(blank=True, null=True, help_text="Emergency exits clear?")
    trip_hazard = models.BooleanField(blank=True, null=True, help_text="Appropriate barriers around kit and cabling secured?")
    warning_signs = models.BooleanField(blank=True, help_text="Warning signs in place?<br><small>(strobe, smoke, power etc.)</small>")
    ear_plugs = models.BooleanField(blank=True, null=True, help_text="Ear plugs issued to crew where needed?")
    hs_location = models.CharField(blank=True, null=True, max_length=255, help_text="Location of Safety Bag/Box")
    extinguishers_location = models.CharField(blank=True, null=True, max_length=255, help_text="Location of fire extinguishers")

    # Small Electrical Checks
    rcds = models.BooleanField(blank=True, null=True, help_text="RCDs installed where needed and tested?")
    supply_test = models.BooleanField(blank=True, null=True, help_text="Electrical supplies tested?<br><small>(using socket tester)</small>")

    # Shared electrical checks
    earthing = models.BooleanField(blank=True, null=True, help_text="Equipment appropriately earthed?<br><small>(truss, stage, generators etc)</small>")
    pat = models.BooleanField(blank=True, null=True, help_text="All equipment in PAT period?")

    # Medium Electrical Checks
    source_rcd = models.BooleanField(blank=True, null=True, help_text="Source RCD protected?<br><small>(if cable is more than 3m long) </small>")
    labelling = models.BooleanField(blank=True, null=True, help_text="Appropriate and clear labelling on distribution and cabling?")
    # First Distro
    fd_voltage_l1 = models.IntegerField(blank=True, null=True, verbose_name="First Distro Voltage L1-N", help_text="L1 - N")
    fd_voltage_l2 = models.IntegerField(blank=True, null=True, verbose_name="First Distro Voltage L2-N", help_text="L2 - N")
    fd_voltage_l3 = models.IntegerField(blank=True, null=True, verbose_name="First Distro Voltage L3-N", help_text="L3 - N")
    fd_phase_rotation = models.BooleanField(blank=True, null=True, verbose_name="Phase Rotation", help_text="Phase Rotation<br><small>(if required)</small>")
    fd_earth_fault = models.IntegerField(blank=True, null=True, verbose_name="Earth Fault Loop Impedance", help_text="Earth Fault Loop Impedance (Z<small>S</small>)")
    fd_pssc = models.IntegerField(blank=True, null=True, verbose_name="PSCC", help_text="Prospective Short Circuit Current")
    # Worst case points
    w1_description = models.CharField(blank=True, null=True, max_length=255, help_text="Description")
    w1_polarity = models.BooleanField(blank=True, null=True, help_text="Polarity Checked?")
    w1_voltage = models.IntegerField(blank=True, null=True, help_text="Voltage")
    w1_earth_fault = models.IntegerField(blank=True, null=True, help_text="Earth Fault Loop Impedance (Z<small>S</small>)")
    w2_description = models.CharField(blank=True, null=True, max_length=255, help_text="Description")
    w2_polarity = models.BooleanField(blank=True, null=True, help_text="Polarity Checked?")
    w2_voltage = models.IntegerField(blank=True, null=True, help_text="Voltage")
    w2_earth_fault = models.IntegerField(blank=True, null=True, help_text="Earth Fault Loop Impedance (Z<small>S</small>)")
    w3_description = models.CharField(blank=True, null=True, max_length=255, help_text="Description")
    w3_polarity = models.BooleanField(blank=True, null=True, help_text="Polarity Checked?")
    w3_voltage = models.IntegerField(blank=True, null=True, help_text="Voltage")
    w3_earth_fault = models.IntegerField(blank=True, null=True, help_text="Earth Fault Loop Impedance (Z<small>S</small>)")

    all_rcds_tested = models.BooleanField(blank=True, null=True, help_text="All circuit RCDs tested?<br><small>(using test button)</small>")
    public_sockets_tested = models.BooleanField(blank=True, null=True, help_text="Public/Performer accessible circuits tested?<br><small>(using socket tester)</small>")

    reviewed_at = models.DateTimeField(null=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True,
                                    verbose_name="Reviewer", on_delete=models.CASCADE)

    inverted_fields = []

    class Meta:
        ordering = ['event']
        permissions = [
            ('review_eventchecklist', 'Can review Event Checklists')
        ]

    @property
    def activity_feed_string(self):
        return str(self.event)

    def get_absolute_url(self):
        return reverse_lazy('ec_detail', kwargs={'pk': self.pk})

    def __str__(self):
        return "%i - %s" % (self.pk, self.event)


@reversion.register
class EventChecklistVehicle(models.Model, RevisionMixin):
    checklist = models.ForeignKey('EventChecklist', related_name='vehicles', blank=True, on_delete=models.CASCADE)
    vehicle = models.CharField(max_length=255)
    driver = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='vehicles', on_delete=models.CASCADE)

    reversion_hide = True

    def __str__(self):
        return "{} driven by {}".format(self.vehicle, str(self.driver))


@reversion.register
class EventChecklistCrew(models.Model, RevisionMixin):
    checklist = models.ForeignKey('EventChecklist', related_name='crew', blank=True, on_delete=models.CASCADE)
    crewmember = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='crewed', on_delete=models.CASCADE)
    role = models.CharField(max_length=255)
    start = models.DateTimeField()
    end = models.DateTimeField()

    reversion_hide = True

    def clean(self):
        if self.start > self.end:
            raise ValidationError('Unless you\'ve invented time travel, crew can\'t finish before they have started.')

    def __str__(self):
        return "{} ({})".format(str(self.crewmember), self.role)

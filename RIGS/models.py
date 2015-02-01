import hashlib
import datetime

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.utils.functional import cached_property
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

    @property
    def name(self):
        return self.get_full_name() + ' "' + self.initials + '"'


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

    @property
    def organisations(self):
        o = []
        for e in Event.objects.filter(person=self).select_related('organisation'):
            if e.organisation and e.organisation not in o:
                o.append(e.organisation)
        return o

    @property
    def latest_events(self):
        return self.event_set.order_by('-start_date').select_related('person', 'organisation', 'venue', 'mic')

    class Meta:
        permissions = (
            ('view_person', 'Can view Persons'),
        )


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

    @property
    def persons(self):
        p = []
        for e in Event.objects.filter(organisation=self).select_related('person'):
            if e.person and e.person not in p:
                p.append(e.person)
        return p

    @property
    def latest_events(self):
        return self.event_set.order_by('-start_date').select_related('person', 'organisation', 'venue', 'mic')

    class Meta:
        permissions = (
            ('view_organisation', 'Can view Organisations'),
        )


class VatManager(models.Manager):
    def current_rate(self):
        return self.find_rate(datetime.datetime.now())

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
    start_at = models.DateTimeField()
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

    class Meta:
        permissions = (
            ('view_venue', 'Can view Venues'),
        )


class EventManager(models.Manager):
    def current_events(self):
        events = self.filter(
            (models.Q(start_date__gte=datetime.date.today(), end_date__isnull=True, dry_hire=False) & ~models.Q(
                status=Event.CANCELLED)) |  # Starts after with no end
            (models.Q(end_date__gte=datetime.date.today(), dry_hire=False) & ~models.Q(
                status=Event.CANCELLED)) |  # Ends after
            (models.Q(dry_hire=True, start_date__gte=datetime.date.today()) & ~models.Q(
                status=Event.CANCELLED)) |  # Active dry hire
            (models.Q(dry_hire=True, checked_in_by__isnull=True) & (
                models.Q(status=Event.BOOKED) | models.Q(status=Event.CONFIRMED))) |  # Active dry hire GT
            models.Q(status=Event.CANCELLED, start_date__gte=datetime.date.today())  # Canceled but not started
        ).order_by('meet_at', 'start_date').select_related('person', 'organisation', 'venue', 'mic')
        return events

    def rig_count(self):
        event_count = self.filter(
            (models.Q(start_date__gte=datetime.date.today(), end_date__isnull=True, dry_hire=False,
                      is_rig=True) & ~models.Q(
                status=Event.CANCELLED)) |  # Starts after with no end
            (models.Q(end_date__gte=datetime.date.today(), dry_hire=False, is_rig=True) & ~models.Q(
                status=Event.CANCELLED)) |  # Ends after
            (models.Q(dry_hire=True, start_date__gte=datetime.date.today(), is_rig=True) & ~models.Q(
                status=Event.CANCELLED)) |  # Active dry hire
            (models.Q(dry_hire=True, checked_in_by__isnull=True, is_rig=True) & (
                models.Q(status=Event.BOOKED) | models.Q(status=Event.CONFIRMED)))  # Active dry hire GT
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
    person = models.ForeignKey('Person', null=True, blank=True)
    organisation = models.ForeignKey('Organisation', blank=True, null=True)
    venue = models.ForeignKey('Venue', blank=True, null=True)
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
    mic = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='event_mic', blank=True, null=True,
                            verbose_name="MIC")

    # Monies
    payment_method = models.CharField(max_length=255, blank=True, null=True)
    payment_received = models.CharField(max_length=255, blank=True, null=True)
    purchase_order = models.CharField(max_length=255, blank=True, null=True)
    collector = models.CharField(max_length=255, blank=True, null=True)

    # Calculated values
    """
    EX Vat
    """
    @property
    def sum_total(self):
        total = 0
        for item in self.items.filter(cost__gt=0):
            total += item.total_cost
        return total

    @cached_property
    def vat_rate(self):
        return VatRate.objects.find_rate(self.start_date)

    @property
    def vat(self):
        return self.sum_total * self.vat_rate.rate

    """
    Inc VAT
    """
    @property
    def total(self):
        return self.sum_total + self.vat

    @property
    def cancelled(self):
        return (self.status == self.CANCELLED)

    @property
    def confirmed(self):
        return (self.status == self.BOOKED or self.status == self.CONFIRMED)

    objects = EventManager()

    def __str__(self):
        return str(self.pk) + ": " + self.name

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
        total = self.payment_set.aggregate(models.Sum('amount'))
        # for payment in self.payment_set.all():
        #     total += payment.amount
        return total

    @property
    def balance(self):
        return self.sum_total - self.payment_total

    def __str__(self):
        return "%i: %s (%.2f)" % (self.pk, self.event, self.balance)

    class Meta:
        permissions = (
            ('view_invoice', 'Can view Invoices'),
        )


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
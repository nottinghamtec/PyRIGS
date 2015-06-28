import hashlib
import datetime

from django.db import models, connection
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.utils.functional import cached_property
from django.utils.encoding import python_2_unicode_compatible
import reversion
import string
import random
from django.core.urlresolvers import reverse_lazy

from decimal import Decimal

# Create your models here.
@python_2_unicode_compatible
class Profile(AbstractUser):
    initials = models.CharField(max_length=5, unique=True, null=True, blank=False)
    phone = models.CharField(max_length=13, null=True, blank=True)
    api_key = models.CharField(max_length=40,blank=True,editable=False, null=True)

    @classmethod
    def make_api_key(cls):
        size=20
        chars=string.ascii_letters + string.digits
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
        return self.get_full_name() + ' "' + self.initials + '"'

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
    def last_edited_at(self):
        versions = reversion.get_for_object(self)
        if versions:
            version = reversion.get_for_object(self)[0]
            return version.revision.date_created
        else:
            return None

    @property
    def last_edited_by(self):
        versions = reversion.get_for_object(self)
        if versions:
            version = reversion.get_for_object(self)[0]
            return version.revision.user
        else:
            return None

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
            if  len(self.notes) > 0:
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
            if  len(self.notes) > 0:
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

    def get_absolute_url(self):
        return reverse_lazy('organisation_detail', kwargs={'pk': self.pk})

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
@python_2_unicode_compatible
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
            (models.Q(start_date__gte=datetime.date.today(), end_date__isnull=True, dry_hire=False) & ~models.Q(status=Event.CANCELLED)) |  # Starts after with no end
            (models.Q(end_date__gte=datetime.date.today(), dry_hire=False) & ~models.Q(status=Event.CANCELLED)) |  # Ends after
            (models.Q(dry_hire=True, start_date__gte=datetime.date.today()) & ~models.Q(status=Event.CANCELLED)) |  # Active dry hire
            (models.Q(dry_hire=True, checked_in_by__isnull=True) & (models.Q(status=Event.BOOKED) | models.Q(status=Event.CONFIRMED))) |  # Active dry hire GT
            models.Q(status=Event.CANCELLED, start_date__gte=datetime.date.today())  # Canceled but not started
        ).order_by('start_date', 'end_date', 'start_time', 'end_time', 'meet_at').select_related('person', 'organisation', 'venue', 'mic')
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
    purchase_order = models.CharField(max_length=255, blank=True, null=True, verbose_name='PO')
    collector = models.CharField(max_length=255, blank=True, null=True, verbose_name='collected by')

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
        #total = self.items.raw(sql)[0]
        #if total.sum_total:
        #    return total.sum_total
        #total = 0.0
        #for item in self.items.filter(cost__gt=0).extra(select="SUM(cost * quantity) AS sum"):
        #    total += item.sum
        total = EventItem.objects.filter(event=self).aggregate(
            sum_total=models.Sum(models.F('cost')*models.F('quantity'), output_field=models.DecimalField(max_digits=10, decimal_places=2))
        )['sum_total']
        if total:
            return total
        return Decimal("0.00")

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

    @property
    def has_start_time(self):
        return self.start_time is not None

    @property
    def has_end_time(self):
        return self.end_time is not None

    objects = EventManager()

    def get_absolute_url(self):
        return reverse_lazy('event_detail', kwargs={'pk': self.pk})

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
        # Manual querying is required for efficiency whilst maintaining floating point arithmetic
        #if connection.vendor == 'postgresql':
        #    sql = "SELECT SUM(amount) AS total FROM \"RIGS_payment\" WHERE invoice_id=%i" % self.id
        #else:
        #    sql = "SELECT id, SUM(amount) AS total FROM RIGS_payment WHERE invoice_id=%i" % self.id
        #total = self.payment_set.raw(sql)[0]
        #if total.total:
        #    return total.total
        #return 0.0
        total = self.payment_set.aggregate(total=models.Sum('amount'))['total']
        if total:
            return total
        return Decimal("0.00")

    @property
    def balance(self):
        return self.sum_total - self.payment_total

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
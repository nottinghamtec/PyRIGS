import datetime
from decimal import Decimal

import pytz
from django.db.models import Q
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property
from reversion import revisions as reversion
from versioning.versioning import RevisionMixin

from RIGS.validators import validate_url
from .utils import filter_by_pk
from .finance import VatRate


class BaseEventManager(models.Manager):
    def event_search(self, q, start, end, status):
        filt = Q()
        if end:
            filt &= Q(start_date__lte=end)
        if start:
            filt &= Q(start_date__gte=start)

        objects = self.all()

        if q:
            objects = self.search(q)

        if len(status) > 0:
            filt &= Q(status__in=status)

        qs = objects.filter(filt).order_by('-start_date')

        # Preselect related for efficiency
        qs.select_related('person', 'organisation', 'venue', 'mic')

        return qs

class EventManager(BaseEventManager):
    def current_events(self):
        events = self.filter(
            (models.Q(start_date__gte=timezone.now(), end_date__isnull=True, dry_hire=False) & ~models.Q(
                status=Event.CANCELLED)) |  # Starts after with no end
            (models.Q(end_date__gte=timezone.now().date(), dry_hire=False) & ~models.Q(
                status=Event.CANCELLED)) |  # Ends after
            (models.Q(dry_hire=True, start_date__gte=timezone.now()) & ~models.Q(
                status=Event.CANCELLED)) |  # Active dry hire
            (models.Q(dry_hire=True, checked_in_by__isnull=True) & (
                models.Q(status=Event.BOOKED) | models.Q(status=Event.CONFIRMED))) |  # Active dry hire GT
            models.Q(status=Event.CANCELLED, start_date__gte=timezone.now())  # Canceled but not started
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

    def active_dry_hires(self):
        return self.filter(dry_hire=True, start_date__gte=timezone.now(), is_rig=True)

    def rig_count(self):
        event_count = self.exclude(status=BaseEvent.CANCELLED).filter(
            (models.Q(start_date__gte=timezone.now(), end_date__isnull=True, dry_hire=False,
                      is_rig=True)) |  # Starts after with no end
            (models.Q(end_date__gte=timezone.now(), dry_hire=False, is_rig=True)) |  # Ends after
            (models.Q(dry_hire=True, start_date__gte=timezone.now(), is_rig=True))  # Active dry hire
        ).count()
        return event_count

    def waiting_invoices(self):
        events = self.filter(
            (
                models.Q(start_date__lte=datetime.date.today(), end_date__isnull=True) |  # Starts before with no end
                models.Q(end_date__lte=datetime.date.today())  # Or has end date, finishes before
            ) & models.Q(invoice__isnull=True) &  # Has not already been invoiced
            models.Q(is_rig=True)  # Is a rig (not non-rig)
        ).order_by('start_date') \
            .select_related('person', 'organisation', 'venue', 'mic') \
            .prefetch_related('items')

        return events

    def search(self, query=None):
        qs = self.get_queryset()
        if query is not None:
            or_lookup = Q(name__icontains=query) | Q(description__icontains=query) | Q(notes__icontains=query)

            or_lookup = filter_by_pk(or_lookup, query)

            try:
                if query[0] == "N":
                    val = int(query[1:])
                    or_lookup = Q(pk=val)  # If string is N###### then do a simple PK filter
            except:  # noqa
                pass

            qs = qs.filter(or_lookup).distinct()  # distinct() is often necessary with Q lookups
        return qs


def find_earliest_event_time(event, datetime_list):
    # If there is no start time defined, pretend it's midnight
    startTimeFaked = False
    if event.has_start_time:
        startDateTime = datetime.datetime.combine(event.start_date, event.start_time)
    else:
        startDateTime = datetime.datetime.combine(event.start_date, datetime.time(00, 00))
        startTimeFaked = True

    # timezoneIssues - apply the default timezone to the naiive datetime
    tz = pytz.timezone(settings.TIME_ZONE)
    startDateTime = tz.localize(startDateTime)
    datetime_list.append(startDateTime)  # then add it to the list

    earliest = min(datetime_list).astimezone(tz)  # find the earliest datetime in the list

    # if we faked it & it's the earliest, better own up
    if startTimeFaked and earliest == startDateTime:
        return event.start_date
    return earliest


class BaseEvent(models.Model, RevisionMixin):
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
    description = models.TextField(blank=True, default='')
    status = models.IntegerField(choices=EVENT_STATUS_CHOICES, default=PROVISIONAL)

    # Timing
    start_date = models.DateField()
    start_time = models.TimeField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    end_time = models.TimeField(blank=True, null=True)

    purchase_order = models.CharField(max_length=255, blank=True, default='', verbose_name='PO')

    class Meta:
        abstract = True

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
    def length(self):
        start = self.earliest_time
        if isinstance(self.earliest_time, datetime.datetime):
            start = self.earliest_time.date()
        end = self.latest_time
        if isinstance(self.latest_time, datetime.datetime):
            end = self.latest_time.date()
        return (end - start).days

    def clean(self):
        errdict = {}
        if self.end_date and self.start_date > self.end_date:
            errdict['end_date'] = ["Unless you've invented time travel, the event can't finish before it has started."]

        startEndSameDay = not self.end_date or self.end_date == self.start_date
        hasStartAndEnd = self.has_start_time and self.has_end_time
        if startEndSameDay and hasStartAndEnd and self.start_time > self.end_time:
            errdict['end_time'] = ["Unless you've invented time travel, the event can't finish before it has started."]
        return errdict

    def __str__(self):
        return f"{self.display_id}: {self.name}"

@reversion.register(follow=['items'])
class Event(BaseEvent):
    mic = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='event_mic', blank=True, null=True,
                        verbose_name="MIC", on_delete=models.CASCADE)
    venue = models.ForeignKey('Venue', blank=True, null=True, on_delete=models.CASCADE)
    notes = models.TextField(blank=True, default='')
    dry_hire = models.BooleanField(default=False)
    is_rig = models.BooleanField(default=True)
    based_on = models.ForeignKey('Event', on_delete=models.SET_NULL, related_name='future_events', blank=True,
                                 null=True)

    access_at = models.DateTimeField(blank=True, null=True)
    meet_at = models.DateTimeField(blank=True, null=True)

    # Dry-hire only
    checked_in_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='event_checked_in', blank=True, null=True,
                                      on_delete=models.CASCADE)

    # Monies
    collector = models.CharField(max_length=255, blank=True, default='', verbose_name='collected by')

    # Authorisation request details
    auth_request_by = models.ForeignKey('Profile', null=True, blank=True, on_delete=models.CASCADE)
    auth_request_at = models.DateTimeField(null=True, blank=True)
    auth_request_to = models.EmailField(blank=True, default='')

    @property
    def display_id(self):
        if self.pk:
            if self.is_rig:
                return f"N{self.pk:05d}"
            return self.pk
        return "????"

    # Calculated values
    """
    EX Vat
    """

    @property
    def sum_total(self):
        total = self.items.aggregate(
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
        # No VAT is owed on internal transfers
        if self.internal:
            return 0
        return Decimal(self.sum_total * self.vat_rate.rate).quantize(Decimal('.01'))

    """
    Inc VAT
    """

    @property
    def total(self):
        return Decimal(self.sum_total + self.vat).quantize(Decimal('.01'))

    @property
    def hs_done(self):
        return self.riskassessment is not None and len(self.checklists.all()) > 0

    @property
    def earliest_time(self):
        """Finds the earliest time defined in the event - this function could return either a tzaware datetime, or a naiive date object"""

        # Put all the datetimes in a list
        datetime_list = []

        if self.access_at:
            datetime_list.append(self.access_at)

        if self.meet_at:
            datetime_list.append(self.meet_at)

        earliest = find_earliest_event_time(self, datetime_list)

        return earliest

    @property
    def internal(self):
        return bool(self.organisation and self.organisation.union_account)

    @property
    def authorised(self):
        if self.internal and hasattr(self, 'authorisation'):
            return self.authorisation.amount == self.total
        else:
            return bool(self.purchase_order)

    @property
    def color(self):
        if self.cancelled:
            return "secondary"
        elif not self.is_rig:
            return "info"
        elif not self.mic:
            return "danger"
        elif self.confirmed and self.authorised:
            if self.dry_hire or self.riskassessment:
               return "success"
            else:
                return "warning"
        else:
            return "warning"

    objects = EventManager()

    def get_absolute_url(self):
        return reverse('event_detail', kwargs={'pk': self.pk})

    def get_edit_url(self):
        return reverse('event_update', kwargs={'pk': self.pk})

    def clean(self):
        errdict = super().clean()

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
    description = models.TextField(blank=True, default='')
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
        return f"{self.event_id}.{self.order}: {self.event.name} | {self.name}"

    @property
    def activity_feed_string(self):
        return f"item {self.name}"


@reversion.register
class EventAuthorisation(models.Model, RevisionMixin):
    event = models.OneToOneField('Event', related_name='authorisation', on_delete=models.CASCADE)
    email = models.EmailField()
    name = models.CharField(max_length=255)
    uni_id = models.CharField(max_length=10, blank=True, default='', verbose_name="University ID")
    account_code = models.CharField(max_length=50, default='', blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="authorisation amount")
    sent_by = models.ForeignKey('Profile', on_delete=models.CASCADE)

    def get_absolute_url(self):
        return reverse('event_detail', kwargs={'pk': self.event_id})

    @property
    def activity_feed_string(self):
        return f"{self.event.display_id} (requested by {self.sent_by.initials})"


class SubhireManager(BaseEventManager):
    def current_events(self):
        events = self.exclude(status=BaseEvent.CANCELLED).filter(
            (models.Q(start_date__gte=timezone.now(), end_date__isnull=True)) |  # Starts after with no end
            (models.Q(end_date__gte=timezone.now().date()))  # Ends after
        ).order_by('start_date', 'end_date', 'start_time', 'end_time').select_related('person', 'organisation')

        return events

    def event_count(self):
        event_count = self.exclude(status=BaseEvent.CANCELLED).filter(
            (models.Q(start_date__gte=timezone.now(), end_date__isnull=True)) |  # Starts after with no end
            (models.Q(end_date__gte=timezone.now()))
        ).count()
        return event_count

@reversion.register
class Subhire(BaseEvent):
    insurance_value = models.DecimalField(max_digits=10, decimal_places=2) # TODO Validate if this is over notifiable threshold
    events = models.ManyToManyField(Event)
    quote = models.URLField(default='', validators=[validate_url])


    objects = SubhireManager()

    @property
    def display_id(self):
        return f"S{self.pk:05d}"

    @property
    def color(self):
        return "purple"

    def get_edit_url(self):
        return reverse('subhire_update', kwargs={'pk': self.pk})

    def get_absolute_url(self):
        return reverse('subhire_detail', kwargs={'pk': self.pk})

    @property
    def earliest_time(self):
        return find_earliest_event_time(self, [])

    class Meta:
        permissions = [
            ('subhire_finance', 'Can see financial data for subhire - insurance values')
        ]

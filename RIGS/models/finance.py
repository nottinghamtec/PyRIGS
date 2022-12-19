from decimal import Decimal

from django.db.models import Q
from django.db import models
from django.urls import reverse
from django.utils import timezone
from reversion import revisions as reversion
from versioning.versioning import RevisionMixin
from .utils import filter_by_pk


class VatManager(models.Manager):
    def current_rate(self):
        return self.find_rate(timezone.now())

    def find_rate(self, date):
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
        return f"{self.comment} {self.start_at} @ {self.as_percent}%"


class InvoiceManager(models.Manager):
    def outstanding_invoices(self):
        # Manual query is the only way I have found to do this efficiently. Not ideal but needs must
        sql = "SELECT * FROM " \
              "(SELECT " \
              "(SELECT COUNT(p.amount) FROM \"RIGS_payment\" AS p WHERE p.invoice_id=\"RIGS_invoice\".id) AS \"payment_count\", " \
              "(SELECT SUM(ei.cost * ei.quantity) FROM \"RIGS_eventitem\" AS ei WHERE ei.event_id=\"RIGS_invoice\".event_id) AS \"cost\", " \
              "(SELECT SUM(p.amount) FROM \"RIGS_payment\" AS p WHERE p.invoice_id=\"RIGS_invoice\".id) AS \"payments\", " \
              "\"RIGS_invoice\".\"id\", \"RIGS_invoice\".\"event_id\", \"RIGS_invoice\".\"invoice_date\", \"RIGS_invoice\".\"void\" FROM \"RIGS_invoice\") " \
              "AS sub " \
              "WHERE (((cost > 0.0) AND (payment_count=0)) OR (cost - payments) <> 0.0) AND void = '0'" \
              "ORDER BY invoice_date"

        query = self.raw(sql)
        return query

    def search(self, query=None):
        qs = self.get_queryset()
        if query is not None:
            or_lookup = Q(event__name__icontains=query)

            or_lookup = filter_by_pk(or_lookup, query)

            # try and parse an int
            try:
                val = int(query)
                or_lookup = or_lookup | Q(event__pk=val)
            except:  # noqa
                # not an integer
                pass

            try:
                if query[0] == "N":
                    val = int(query[1:])
                    or_lookup = Q(event__pk=val)  # If string is Nxxxxx then filter by event number
                elif query[0] == "#":
                    val = int(query[1:])
                    or_lookup = Q(pk=val)  # If string is #xxxxx then filter by invoice number
            except:  # noqa
                pass

            qs = qs.filter(or_lookup).distinct()  # distinct() is often necessary with Q lookups
        return qs


@reversion.register(follow=['payment_set'])
class Invoice(models.Model, RevisionMixin):
    event = models.OneToOneField('Event', on_delete=models.CASCADE)
    invoice_date = models.DateField(auto_now_add=True)
    void = models.BooleanField(default=False)

    reversion_perm = 'RIGS.view_invoice'

    objects = InvoiceManager()

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
        return reverse('invoice_detail', kwargs={'pk': self.pk})

    @property
    def activity_feed_string(self):
        return f"{self.display_id} for Event {self.event.display_id}"

    def __str__(self):
        return f"{self.display_id}: {self.event} (£{self.balance:.2f})"

    @property
    def display_id(self):
        return f"#{self.pk:05d}"

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
    method = models.CharField(max_length=2, choices=METHODS, default='', blank=True)

    reversion_hide = True

    def __str__(self):
        return f"{self.get_method_display()}: {self.amount}"

    @property
    def activity_feed_string(self):
        return f"payment of £{self.amount}"
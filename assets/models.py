import re

from django.core.exceptions import ValidationError
from django.db import models, connection
from django.db.models import Q
from django.urls import reverse
from reversion import revisions as reversion
from reversion.models import Version

from RIGS.models import Profile, ContactableManager
from versioning.versioning import RevisionMixin


class AssetCategory(models.Model):
    name = models.CharField(max_length=80)

    class Meta:
        verbose_name = 'Asset Category'
        verbose_name_plural = 'Asset Categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class AssetStatus(models.Model):
    name = models.CharField(max_length=80)
    should_show = models.BooleanField(
        default=True, help_text="Should this be shown by default in the asset list.")
    display_class = models.CharField(max_length=80, blank=True, help_text="HTML class to be appended to alter display of assets with this status, such as in the list.")

    class Meta:
        verbose_name = 'Asset Status'
        verbose_name_plural = 'Asset Statuses'
        ordering = ['name']

    def __str__(self):
        return self.name


@reversion.register
class Supplier(models.Model, RevisionMixin):
    name = models.CharField(max_length=80)
    phone = models.CharField(max_length=15, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    address = models.TextField(blank=True, default="")

    notes = models.TextField(blank=True, default="")

    objects = ContactableManager()

    class Meta:
        ordering = ['name']

    def get_absolute_url(self):
        return reverse('supplier_detail', kwargs={'pk': self.pk})

    def __str__(self):
        return self.name


class Connector(models.Model):
    description = models.CharField(max_length=80)
    current_rating = models.DecimalField(decimal_places=2, max_digits=10, help_text='Amps')
    voltage_rating = models.IntegerField(help_text='Volts')
    num_pins = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return self.description


class CableType(models.Model):
    circuits = models.IntegerField(default=1)
    cores = models.IntegerField(default=3)
    plug = models.ForeignKey(Connector, on_delete=models.CASCADE,
                             related_name='plug')
    socket = models.ForeignKey(Connector, on_delete=models.CASCADE,
                               related_name='socket')

    class Meta:
        ordering = ['plug', 'socket', '-circuits']
        unique_together = ['plug', 'socket', 'circuits', 'cores']

    def __str__(self):
        if self.plug and self.socket:
            return f"{self.plug.description} → {self.socket.description}"
        else:
            return "Unknown"

    def get_absolute_url(self):
        return reverse('cable_type_detail', kwargs={'pk': self.pk})


class AssetManager(models.Manager):
    def search(self, query=None):
        qs = self.get_queryset()
        if query is not None:
            or_lookup = (Q(asset_id__exact=query.upper()) | Q(description__icontains=query) | Q(serial_number__exact=query) | Q(nickname__icontains=query))
            qs = qs.filter(or_lookup).distinct()  # distinct() is often necessary with Q lookups
        return qs


def get_available_asset_id(wanted_prefix=""):
    last_asset = Asset.objects.filter(asset_id_prefix=wanted_prefix).last()
    last_asset_id = last_asset.asset_id_number if last_asset else 0
    return wanted_prefix + str(last_asset_id + 1)


def validate_positive(value):
    if value < 0:
        raise ValidationError("A price cannot be negative")


@reversion.register
class Asset(models.Model, RevisionMixin):
    parent = models.ForeignKey(to='self', related_name='asset_parent',
                               blank=True, null=True, on_delete=models.SET_NULL)
    asset_id = models.CharField(max_length=15, unique=True)
    description = models.CharField(max_length=120)
    category = models.ForeignKey(to=AssetCategory, on_delete=models.CASCADE)
    status = models.ForeignKey(to=AssetStatus, on_delete=models.CASCADE)
    serial_number = models.CharField(max_length=150, blank=True)
    purchased_from = models.ForeignKey(to=Supplier, on_delete=models.SET_NULL, blank=True, null=True, related_name="assets")
    date_acquired = models.DateField()
    date_sold = models.DateField(blank=True, null=True)
    purchase_price = models.DecimalField(blank=True, null=True, decimal_places=2, max_digits=10, validators=[validate_positive])
    replacement_cost = models.DecimalField(null=True, decimal_places=2, max_digits=10, validators=[validate_positive])
    comments = models.TextField(blank=True)
    nickname = models.CharField(max_length=120, blank=True)

    # Audit
    last_audited_at = models.DateTimeField(blank=True, null=True)
    last_audited_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, related_name='audited_by', blank=True, null=True)

    # Cable assets
    is_cable = models.BooleanField(default=False)
    cable_type = models.ForeignKey(to=CableType, blank=True, null=True, on_delete=models.SET_NULL)
    length = models.DecimalField(decimal_places=2, max_digits=10,
                                 blank=True, null=True, help_text='m')
    csa = models.DecimalField(decimal_places=2, max_digits=10,
                              blank=True, null=True, help_text='mm²')

    # Hidden asset_id components
    # For example, if asset_id was "C1001" then asset_id_prefix would be "C" and number "1001"
    asset_id_prefix = models.CharField(max_length=8, default="")
    asset_id_number = models.IntegerField(default=1)

    reversion_perm = 'assets.asset_finance'

    objects = AssetManager()

    class Meta:
        ordering = ['asset_id_prefix', 'asset_id_number']
        permissions = [
            ('asset_finance', 'Can see financial data for assets')
        ]

    def __str__(self):
        return f"{self.asset_id} | {self.description}"

    def get_absolute_url(self):
        return reverse('asset_detail', kwargs={'pk': self.asset_id})

    def clean(self):
        errdict = {}
        if self.date_sold and self.date_acquired > self.date_sold:
            errdict["date_sold"] = ["Cannot sell an item before it is acquired"]

        self.asset_id = self.asset_id.upper()
        asset_search = re.search("^([a-zA-Z0-9]*?[a-zA-Z]?)([0-9]+)$", self.asset_id)
        if asset_search is None:
            errdict["asset_id"] = [
                "An Asset ID can only consist of letters and numbers, with a final number"]

        if self.is_cable:
            if not self.length or self.length <= 0:
                errdict["length"] = ["The length of a cable must be more than 0"]
            if not self.csa or self.csa <= 0:
                errdict["csa"] = ["The CSA of a cable must be more than 0"]
            if not self.cable_type:
                errdict["cable_type"] = ["A cable must have a type"]

        if errdict != {}:  # If there was an error when validation
            raise ValidationError(errdict)

    @property
    def activity_feed_string(self):
        return str(self)

    @property
    def display_id(self):
        return str(self.asset_id)

    @property
    def display_name(self):
        return f"{self.display_id} | {self.description}"

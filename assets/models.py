import re

from django.core.exceptions import ValidationError
from django.db import models, connection
from django.db.models.signals import pre_save
from django.dispatch.dispatcher import receiver
from django.urls import reverse
from reversion import revisions as reversion
from reversion.models import Version

from RIGS.models import RevisionMixin, Profile


class AssetCategory(models.Model):
    class Meta:
        verbose_name = 'Asset Category'
        verbose_name_plural = 'Asset Categories'
        ordering = ['name']

    name = models.CharField(max_length=80)

    def __str__(self):
        return self.name


class AssetStatus(models.Model):
    class Meta:
        verbose_name = 'Asset Status'
        verbose_name_plural = 'Asset Statuses'
        ordering = ['name']

    name = models.CharField(max_length=80)
    should_show = models.BooleanField(
        default=True, help_text="Should this be shown by default in the asset list.")
    display_class = models.CharField(max_length=80, blank=True, null=True, help_text="HTML class to be appended to alter display of assets with this status, such as in the list.")

    def __str__(self):
        return self.name


@reversion.register
class Supplier(models.Model, RevisionMixin):
    class Meta:
        ordering = ['name']

    name = models.CharField(max_length=80)
    phone = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    notes = models.TextField(blank=True, null=True)

    def get_absolute_url(self):
        return reverse('supplier_list')

    def __str__(self):
        return self.name


class Connector(models.Model):
    description = models.CharField(max_length=80)
    current_rating = models.DecimalField(decimal_places=2, max_digits=10, help_text='Amps')
    voltage_rating = models.IntegerField(help_text='Volts')
    num_pins = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return self.description


# Things are nullable that shouldn't be because I didn't properly fix the data structure when moving this to its own model...
class CableType(models.Model):
    class Meta:
        ordering = ['plug', 'socket', '-circuits']

    circuits = models.IntegerField(default=1)
    cores = models.IntegerField(default=3)
    plug = models.ForeignKey(Connector, on_delete=models.CASCADE,
                             related_name='plug', null=True)
    socket = models.ForeignKey(Connector, on_delete=models.CASCADE,
                               related_name='socket', null=True)

    def __str__(self):
        if self.plug and self.socket:
            return "%s → %s" % (self.plug.description, self.socket.description)
        else:
            return "Unknown"


@reversion.register
class Asset(models.Model, RevisionMixin):
    class Meta:
        ordering = ['asset_id_prefix', 'asset_id_number']
        permissions = [
            ('asset_finance', 'Can see financial data for assets')
        ]

    parent = models.ForeignKey(to='self', related_name='asset_parent',
                               blank=True, null=True, on_delete=models.SET_NULL)
    asset_id = models.CharField(max_length=15, unique=True)
    description = models.CharField(max_length=120)
    category = models.ForeignKey(to=AssetCategory, on_delete=models.CASCADE)
    status = models.ForeignKey(to=AssetStatus, on_delete=models.CASCADE)
    serial_number = models.CharField(max_length=150, blank=True)
    purchased_from = models.ForeignKey(to=Supplier, on_delete=models.CASCADE, blank=True, null=True, related_name="assets")
    date_acquired = models.DateField()
    date_sold = models.DateField(blank=True, null=True)
    purchase_price = models.DecimalField(blank=True, null=True, decimal_places=2, max_digits=10)
    salvage_value = models.DecimalField(blank=True, null=True, decimal_places=2, max_digits=10)
    comments = models.TextField(blank=True)

    # Audit
    last_audited_at = models.DateTimeField(blank=True, null=True)
    last_audited_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, related_name='audited_by', blank=True, null=True)

    # Cable assets
    is_cable = models.BooleanField(default=False)
    cable_type = models.ForeignKey(to=CableType, blank=True, null=True, on_delete=models.SET_NULL)
    length = models.DecimalField(decimal_places=1, max_digits=10,
                                 blank=True, null=True, help_text='m')
    csa = models.DecimalField(decimal_places=2, max_digits=10,
                              blank=True, null=True, help_text='mm²')

    # Hidden asset_id components
    # For example, if asset_id was "C1001" then asset_id_prefix would be "C" and number "1001"
    asset_id_prefix = models.CharField(max_length=8, default="")
    asset_id_number = models.IntegerField(default=1)

    reversion_perm = 'assets.asset_finance'

    def get_available_asset_id(wanted_prefix=""):
        sql = """
        SELECT a.asset_id_number+1
        FROM assets_asset a
        LEFT OUTER JOIN assets_asset b ON
            (a.asset_id_number + 1 = b.asset_id_number AND
            a.asset_id_prefix = b.asset_id_prefix)
        WHERE b.asset_id IS NULL AND a.asset_id_number >= %s AND a.asset_id_prefix = %s;
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [9000, wanted_prefix])
            row = cursor.fetchone()
            if row is None or row[0] is None:
                return 9000
            else:
                return row[0]

    def get_absolute_url(self):
        return reverse('asset_detail', kwargs={'pk': self.asset_id})

    def __str__(self):
        out = str(self.asset_id) + ' - ' + self.description
        if self.is_cable and self.cable_type is not None:
            out += '{} - {}m - {}'.format(self.cable_type.plug, self.length, self.cable_type.socket)
        return out

    def clean(self):
        errdict = {}
        if self.date_sold and self.date_acquired > self.date_sold:
            errdict["date_sold"] = ["Cannot sell an item before it is acquired"]

        self.asset_id = self.asset_id.upper()
        asset_search = re.search("^([a-zA-Z0-9]*?[a-zA-Z]?)([0-9]+)$", self.asset_id)
        if asset_search is None:
            errdict["asset_id"] = [
                "An Asset ID can only consist of letters and numbers, with a final number"]

        if self.purchase_price and self.purchase_price < 0:
            errdict["purchase_price"] = ["A price cannot be negative"]

        if self.salvage_value and self.salvage_value < 0:
            errdict["salvage_value"] = ["A price cannot be negative"]

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


@receiver(pre_save, sender=Asset)
def pre_save_asset(sender, instance, **kwargs):
    """Automatically fills in hidden members on database access"""
    asset_search = re.search("^([a-zA-Z0-9]*?[a-zA-Z]?)([0-9]+)$", instance.asset_id)
    if asset_search is None:
        instance.asset_id += "1"
    asset_search = re.search("^([a-zA-Z0-9]*?[a-zA-Z]?)([0-9]+)$", instance.asset_id)
    instance.asset_id_prefix = asset_search.group(1)
    instance.asset_id_number = int(asset_search.group(2))

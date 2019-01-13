from django.db import models
from django.urls import reverse

import datetime


class AssetCategory(models.Model):
    class Meta:
        verbose_name = 'Asset Category'
        verbose_name_plural = 'Asset Categories'
    name = models.CharField(max_length=80)

    def __str__(self):
        return self.name


class AssetStatus(models.Model):
    class Meta:
        verbose_name = 'Asset Status'
        verbose_name_plural = 'Asset Statuses'
    name = models.CharField(max_length=80)

    def __str__(self):
        return self.name


class Supplier(models.Model):
    name = models.CharField(max_length=80)

    def get_absolute_url(self):
        return reverse('supplier_list')

    def __str__(self):
        return self.name


class BaseAsset(models.Model):
    class Meta:
        abstract = True

    parent = models.ForeignKey(to='self', related_name='asset_parent', blank=True, null=True, on_delete=models.SET_NULL)
    asset_id = models.CharField(max_length=10)
    description = models.CharField(max_length=120)
    category = models.ForeignKey(to=AssetCategory, on_delete=models.CASCADE)
    status = models.ForeignKey(to=AssetStatus, on_delete=models.CASCADE)
    serial_number = models.CharField(max_length=150, blank=True)
    purchased_from = models.ForeignKey(to=Supplier, on_delete=models.CASCADE, blank=True, null=True)
    date_acquired = models.DateField()
    date_sold = models.DateField(blank=True, null=True)
    purchase_price = models.DecimalField(blank=True, null=True, decimal_places=2, max_digits=10)
    salvage_value = models.DecimalField(blank=True, null=True, decimal_places=2, max_digits=10)
    comments = models.TextField(blank=True)
    next_sched_maint = models.DateField(blank=True, null=True)

    # Cable assets
    is_cable = models.BooleanField(default=False)
    length = models.DecimalField(decimal_places=1, max_digits=10, blank=True, null=True)

    def get_absolute_url(self):
        return reverse('asset_detail', kwargs={'pk': self.pk})

    def __str__(self):
        return str(self.asset_id) + ' - ' + self.description


class Asset(BaseAsset):
    pass


class Connector(models.Model):
    description = models.CharField(max_length=80)
    current_rating = models.DecimalField(decimal_places=2, max_digits=10, help_text='Amps')
    voltage_rating = models.IntegerField(help_text='Volts')
    num_pins = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return self.description


class Cable(BaseAsset):
    plug = models.ForeignKey(Connector, on_delete=models.SET_NULL, related_name='plug', null=True)
    socket = models.ForeignKey(Connector, on_delete=models.SET_NULL, related_name='socket', null=True)
    length = models.DecimalField(decimal_places=1, max_digits=10, blank=True, null=True, help_text='m')
    csa = models.DecimalField(decimal_places=2, max_digits=10, blank=True, null=True, help_text='mm^2')
    circuits = models.IntegerField(blank=True, null=True)
    cores = models.IntegerField(blank=True, null=True)

    def cable_resistance(self):
        rho = 0.0000000168
        return (rho * self.length) / (self.csa * 1000000)

    def __str__(self):
        return '{} - {}m - {}'.format(self.plug, self.length, self.socket)

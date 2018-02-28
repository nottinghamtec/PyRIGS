from django.db import models

class AssetCategory(models.Model):
    class Meta:
        verbose_name = 'Asset Category'
        verbose_name_plural = 'Asset Categories'
    name = models.CharField(max_length=80)


class AssetStatus(models.Model):
    class Meta:
        verbose_name = 'Asset Status'
        verbose_name_plural = 'Asset Statuses'
    name = models.CharField(max_length=80)


class Supplier(models.Model):
    name = models.CharField(max_length=80)


class Collection(models.Model):
    name = models.CharField(max_length=80)


class Asset(models.Model):
    asset_id = models.IntegerField()
    description = models.CharField(max_length=120)
    category = models.ForeignKey(to=AssetCategory, on_delete=models.CASCADE)
    status = models.ForeignKey(to=AssetStatus, on_delete=models.CASCADE)
    serial_number = models.CharField(max_length=150, blank=True, null=True)
    purchased_from = models.ForeignKey(to=Supplier, on_delete=models.CASCADE, blank=True, null=True)
    date_acquired = models.DateField()
    date_sold = models.DateField(blank=True, null=True)
    purchase_price = models.IntegerField()
    salvage_value = models.IntegerField(blank=True, null=True)
    comments = models.TextField(blank=True, null=True)
    next_sched_maint = models.DateField(blank=True, null=True)

    collection = models.ForeignKey(to=Collection, on_delete=models.CASCADE)

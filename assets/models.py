from django.db import models
import reversion


# Create your models here.
class Suppliers(models.Model):
    name = models.CharField(max_length=100)


class AbstractAsset(models.Model):
    STATUS_LOST = 1
    STATUS_ACTIVE = 2
    STATUS_INACTIVE = 3
    STATUS_BROKEN = 4
    STATUS_SCRAPPED = 5
    STATUS_NOT_BUILT = 6
    STATUS_SOLD = 7

    STATUS_CHOICES = (
        (STATUS_LOST, 'Lost'),
        (STATUS_ACTIVE, 'Active'),
        (STATUS_INACTIVE, 'Inactive'),
        (STATUS_BROKEN, 'Broken'),
        (STATUS_SCRAPPED, 'Scrapped'),
        (STATUS_NOT_BUILT, 'Not Yet Built'),
        (STATUS_SOLD, 'Sold'),
    )

    status = models.IntegerField(choices=STATUS_CHOICES)
    notes = models.TextField(blank=True, null=True)
    # test_period  # decide what to do with this later

    class Meta:
        abstract = True


class Asset(models.Model):
    CATEGORY_GENERAL = 1
    CATEGORY_CASE = 2
    CATEGORY_COMMS = 3
    CATEGORY_DECKING = 4
    CATEGORY_OFFICE = 5
    CATEGORY_SOUND = 10
    CATEGORY_LIGHTING = 20
    CATEGORY_VIDEO = 30
    CATEGORY_RIGGING = 40
    CATEGORY_TRUSS = 41
    CATEGORY_LADDERS = 42
    CATEGORY_POWER = 50
    CATEGORY_DISTRO = 51

    CATEGORY_CHOICES = (
        (CATEGORY_SOUND, 'Sound'),
        (CATEGORY_LIGHTING, 'Lighting'),
        ('Other', (
            (CATEGORY_GENERAL, 'General'),
            (CATEGORY_CASE, 'Case'),
            (CATEGORY_COMMS, 'Comms'),
            (CATEGORY_DECKING, 'Decking'),
            (CATEGORY_OFFICE, 'Office'),
        )),

    )

    name = models.CharField(max_length=255)
    serial_number = models.CharField(max_length=255)
    date_acquired = models.DateField(null=True, blank=True)
    date_sold = models.DateField(null=True, blank=True)
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2)
    replacement_price = models.DecimalField(max_digits=10, decimal_places=2)


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

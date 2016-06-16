import reversion
from django.db import models
from django.conf import settings
from django.utils.encoding import python_2_unicode_compatible

# Create your models here.
class Hire(models.Model):
    WE_TRANSPORT = 0
    THEY_TRANSPORT = 1
    TRANSPORT_CHOICES = (
        (WE_TRANSPORT, 'TEC Transport'),
        (THEY_TRANSPORT, 'Provider Transports'),
    )

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    provider = models.ForeignKey('Provider', blank=True, null=True)

    start_date = models.DateField()
    end_date = models.DateField()

    start_transport = models.IntegerField(
        choices=TRANSPORT_CHOICES, blank=True, null=True)

    mic = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='hire_mic', blank=True, null=True,
                            verbose_name="MIC")

class Provider(models.Model):
    name = models.CharField(max_length=50)
    phone = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)

    address = models.TextField(blank=True, null=True)

    notes = models.TextField(blank=True, null=True)

    @property
    def latest_hires(self):
        return self.hire_set.order_by('-start_date').select_related()

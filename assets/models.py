from django.db import models
import reversion

# Create your models here.
class Suppliers(models.Model):
	name = models.CharField(max_length=100)
	address = models.TextField()
    phone = models.CharField(max_length=13, null=True, blank=True)
	company_number = models.IntegerField()

class AbstractAsset(object):
    purchase_cost = models.DecimalField(max_digits=10, decimal_places=2)
    purchase_date = models.DateField(blank=True, null=True)

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
import hashlib
import reversion

# Create your models here.
class Profile(AbstractUser):
    initials = models.CharField(max_length=5, unique=True)
    phone = models.CharField(max_length=13, null=True, blank=True)

    @property
    def profile_picture (self):
        url = ""
        if settings.USE_GRAVATAR or settings.USE_GRAVATAR is None:
            url = "https://www.gravatar.com/avatar/" + hashlib.md5(self.email).hexdigest() + "?d=identicon&s=500"
        return url

@reversion.register
class Person(models.Model):
    name = models.CharField(max_length=50)
    phone = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)

    address = models.TextField(blank=True, null=True)

    notes = models.TextField(blank=True, null=True)

    def __unicode__(self):
        string = self.name
        if len(self.notes) > 0:
            string += "*"
        return string
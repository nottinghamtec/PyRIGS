from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
import hashlib
import reversion

# Create your models here.
class Profile(AbstractUser):
    initials = models.CharField(max_length=5, unique=True, null=True, blank=True)
    phone = models.CharField(max_length=13, null=True, blank=True)

    @property
    def profile_picture (self):
        url = ""
        if settings.USE_GRAVATAR or settings.USE_GRAVATAR is None:
            url = "https://www.gravatar.com/avatar/" + hashlib.md5(self.email).hexdigest() + "?d=identicon&s=500"
        return url

class RevisionMixin(object):
    @property
    def last_edited_at(self):
        version = reversion.get_for_object(self)[0]
        return version.revision.date_created

    @property
    def last_edited_by(self):
        version = reversion.get_for_object(self)[0]
        return version.revision.user


@reversion.register
class Person(models.Model, RevisionMixin):
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

@reversion.register
class Organisation(models.Model, RevisionMixin):
    name = models.CharField(max_length=50)
    phone = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)

    address = models.TextField(blank=True, null=True)

    notes = models.TextField(blank=True, null=True)
    union_account = models.BooleanField(default=False)

    def __unicode__(self):
        string = self.name
        if len(self.notes) > 0:
            string += "*"
        return string


@reversion.register
class VatRate(models.Model, RevisionMixin):
    start_at = models.DateTimeField()
    rate = models.DecimalField(max_digits=6, decimal_places=6)
    comment = models.CharField(max_length=255)

    def __unicode__(self):
        return self.comment + " " + self.start_at + " @ " + self.rate
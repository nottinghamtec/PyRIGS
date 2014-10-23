from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
import hashlib

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
import uuid
from django.db import models

from datetime import datetime, timedelta

from django.conf import settings


class AuthAttemptManager(models.Manager):
    expiryMinutes = 10

    def get_acceptable(self):
        oldestAcceptableNonce = datetime.now() - timedelta(minutes=self.expiryMinutes)
        return super(AuthAttemptManager, self).get_queryset().filter(created__gte=oldestAcceptableNonce)

    def purge_unacceptable(self):
        oldestAcceptableNonce = datetime.now() - timedelta(minutes=self.expiryMinutes)
        super(AuthAttemptManager, self).get_queryset().filter(created__lt=oldestAcceptableNonce).delete()


def gen_nonce():
    # return "THISISANONCETHATWEWILLREUSE"
    return uuid.uuid4()


class AuthAttempt(models.Model):
    nonce = models.CharField(max_length=25, default=gen_nonce)
    created = models.DateTimeField(auto_now=True)



    objects = AuthAttemptManager()

    def __str__(self):
        return "AuthAttempt at " + str(self.created)


class DiscourseUserLink(models.Model):
    django_user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )

    discourse_user_id = models.IntegerField(unique=True)

    def __str__(self):
        return "{} - {}".format(self.discourse_user_id, str(self.django_user))

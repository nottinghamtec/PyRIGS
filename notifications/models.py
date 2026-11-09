from django.conf import settings
from django.db import models
from django.db.models import Q


class PushSubscription(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="push_subscriptions", on_delete=models.CASCADE)
    endpoint = models.TextField(unique=True)
    p256dh = models.CharField(max_length=255)
    auth = models.CharField(max_length=255)
    user_agent = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} ({self.user_agent[:40] or 'unknown device'})"

    @property
    def info(self):
        return {"endpoint": self.endpoint, "keys": {"p256dh": self.p256dh, "auth": self.auth}}


class Notification(models.Model):
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="notifications", on_delete=models.CASCADE)
    kind = models.CharField(max_length=40)
    title = models.CharField(max_length=120)
    body = models.TextField(blank=True)
    url = models.CharField(max_length=500, blank=True)
    tag = models.CharField(max_length=100, blank=True)
    dedupe_key = models.CharField(max_length=200, blank=True)
    send_email = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        indexes = [models.Index(fields=["recipient", "-created_at"])]
        constraints = [
            models.UniqueConstraint(
                fields=["recipient", "dedupe_key"],
                condition=~Q(dedupe_key=""),
                name="unique_notification_dedupe_key",
            )
        ]

    def __str__(self):
        return f"{self.title} for {self.recipient}"


class NotificationPreference(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="notification_preferences", on_delete=models.CASCADE
    )
    kind = models.CharField(max_length=40)
    push = models.BooleanField()
    email = models.BooleanField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "kind"], name="unique_notification_preference")]

    def __str__(self):
        return f"{self.user}: {self.kind}"

from django.conf import settings
from django.db import models


class BadgeAward(models.Model):
    """A badge someone has earned. Badges themselves are defined in code (badges/registry.py)."""

    profile = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="badge_awards", on_delete=models.CASCADE)
    slug = models.SlugField(max_length=50)
    # When the badge was actually achieved (e.g. the date of the 10th rig), not when the job noticed
    awarded_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    EMAIL_PENDING = "pending"
    EMAIL_SENT = "sent"
    EMAIL_SKIPPED = "skipped"
    EMAIL_OPTED_OUT = "opted_out"
    EMAIL_CHOICES = (
        (EMAIL_PENDING, "Waiting to be sent"),
        (EMAIL_SENT, "Sent"),
        # Not worth telling them: made before badges were live, during a reset, or achieved long ago
        (EMAIL_SKIPPED, "Not sent (backfill)"),
        (EMAIL_OPTED_OUT, "Not sent (opted out)"),
    )
    email = models.CharField(max_length=10, choices=EMAIL_CHOICES, default=EMAIL_SKIPPED)
    emailed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["profile", "slug"], name="unique_badge_per_profile")]
        ordering = ["-awarded_at"]

    @property
    def badge(self):
        from badges.registry import BADGES

        return BADGES.get(self.slug)

    def __str__(self):
        badge = self.badge
        return f"{self.profile} - {badge.name if badge else self.slug}"


class BadgeSettings(models.Model):
    """Single-row switches so features can be deployed and checked before members see them."""

    badges_live = models.BooleanField(
        default=False,
        help_text="Show badges to members. While off, awards are still made by the scheduled job but only people "
        "with the View Badges permission (and superusers, if allowed below) can see them.",
    )
    badges_superusers = models.BooleanField(
        "badges visible for superusers",
        default=False,
        help_text="Let superusers see badges before they're live.",
    )
    tech_rider_live = models.BooleanField(
        default=False,
        help_text="Let members view their Tech Rider. While off, only people with the View Tech Rider permission "
        "(and superusers, if allowed below) can view theirs.",
    )
    tech_rider_superusers = models.BooleanField(
        "Tech Rider visible for superusers",
        default=False,
        help_text="Let superusers view Tech Riders before they're live. Superusers who can see Tech Rider can view "
        "anyone's, to check them.",
    )

    class Meta:
        verbose_name = "badge settings"
        verbose_name_plural = "badge settings"
        # Grant these to let someone see a feature for themselves before it's live
        permissions = [
            ("view_badges", "View Badges"),
            ("view_tech_rider", "View Tech Rider"),
        ]

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "Badge settings"

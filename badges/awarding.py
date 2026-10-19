import datetime
import logging
from collections import defaultdict

import premailer
from django.conf import settings
from django.contrib.staticfiles import finders
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.template.loader import get_template
from django.urls import reverse
from django.utils import timezone

from RIGS.models import Profile

from badges.models import BadgeAward, BadgeSettings
from badges.registry import BADGES
from badges.stats import ProfileStats, build_history, to_datetime

logger = logging.getLogger(__name__)

# Only email about badges achieved this recently. Anything older is backfill (a new badge being added, or
# history catching up) and would just be noise.
EMAIL_WINDOW = datetime.timedelta(days=14)


def earned_badges(stats):
    """{slug: datetime achieved} for every badge this person has earned according to the current rules."""
    earned = {}
    for badge in BADGES.values():
        achieved = badge.rule(stats)
        if achieved is not None:
            earned[badge.slug] = to_datetime(achieved)
    return earned


def award_badges(profiles=None, dry_run=False, reset=False, live=None):
    """
    Work out everyone's badges and save any new ones.

    Returns a list of (profile, badge, achieved, emailed) for the awards that were (or, with dry_run, would be) made,
    where emailed says whether the award is queued to be emailed.
    Existing awards are never removed unless reset is set, which wipes them first so everything is recomputed.
    Inactive accounts are skipped (and, with reset, lose any awards they had).

    New awards are only queued for emailing if badges are live, this isn't a reset, and they were achieved recently.
    Pass live to pretend badges are (or aren't) live, e.g. to preview going live with a dry run.
    """
    profiles = Profile.objects.all() if profiles is None else profiles
    history = build_history()
    new_awards = []
    live = BadgeSettings.load().badges_live if live is None else live
    notify = live and not reset
    cutoff = timezone.now() - EMAIL_WINDOW

    with transaction.atomic():
        if reset and not dry_run:
            BadgeAward.objects.filter(profile__in=profiles).delete()
        # Inactive accounts (mostly people who've left) don't earn badges
        profiles = profiles.filter(is_active=True)
        existing = set(BadgeAward.objects.filter(profile__in=profiles).values_list("profile_id", "slug"))
        if reset and dry_run:
            existing = set()

        for profile in profiles.order_by("pk"):
            earned = earned_badges(ProfileStats(profile, history))
            for slug, achieved in earned.items():
                if (profile.pk, slug) not in existing:
                    new_awards.append((profile, BADGES[slug], achieved, notify and achieved >= cutoff))

        if not dry_run:
            BadgeAward.objects.bulk_create(
                [
                    BadgeAward(
                        profile=profile,
                        slug=badge.slug,
                        awarded_at=achieved,
                        email=BadgeAward.EMAIL_PENDING if emailed else BadgeAward.EMAIL_SKIPPED,
                    )
                    for profile, badge, achieved, emailed in new_awards
                ],
                ignore_conflicts=True,
            )
    return new_awards


def pending_emails(extra=()):
    """{profile: [awards]} for everyone with badges waiting to be emailed, plus any unsaved extra awards."""
    pending = defaultdict(list)
    saved = BadgeAward.objects.filter(email=BadgeAward.EMAIL_PENDING).select_related("profile")
    for award in sorted([*saved, *extra], key=lambda award: award.awarded_at):
        if award.badge:
            pending[award.profile].append(award)
    return pending


def send_badge_emails(dry_run=False, live=None, extra=()):
    """
    Send one email per person listing all of their newly earned badges.

    Returns a list of (profile, [awards], outcome) where outcome is "sent", "would send", "opted out" or "failed".
    Nothing is sent while badges aren't live; pending awards wait until they are.
    For a dry run, extra (unsaved) awards can be included and live overridden, to preview what would go out.
    """
    live = BadgeSettings.load().badges_live if live is None else live
    if not live:
        return []
    if not dry_run and extra:
        raise ValueError("Unsaved awards can only be previewed")

    results = []
    for profile, awards in pending_emails(extra).items():
        ids = [award.pk for award in awards]
        if not profile.badge_emails or not profile.email or not profile.is_active:
            if not dry_run:
                BadgeAward.objects.filter(pk__in=ids).update(email=BadgeAward.EMAIL_OPTED_OUT)
            results.append((profile, awards, "opted out"))
            continue
        if dry_run:
            results.append((profile, awards, "would send"))
            continue
        try:
            _send(profile, awards)
        except Exception:  # One bad address shouldn't stop everyone else's; try again tomorrow
            logger.exception("Couldn't send badge email to %s", profile)
            results.append((profile, awards, "failed"))
            continue
        BadgeAward.objects.filter(pk__in=ids).update(email=BadgeAward.EMAIL_SENT, emailed_at=timezone.now())
        results.append((profile, awards, "sent"))
    return results


def _send(profile, awards):
    base = "https://" + settings.DOMAIN
    context = {
        "profile": profile,
        "awards": awards,
        "profile_url": base + reverse("profile_detail"),
        "badges_url": base + reverse("badge_list"),
        "settings_url": base + reverse("profile_update_self"),
    }
    if len(awards) == 1:
        subject = f"You've earned a badge: {awards[0].badge.name}"
    else:
        subject = f"You've earned {len(awards)} new badges"
    msg = EmailMultiAlternatives(
        subject,
        get_template("badges/email/badges_earned.txt").render(context),
        to=[profile.email],
    )
    css = finders.find("css/email.css")
    html = premailer.Premailer(
        get_template("badges/email/badges_earned.html").render(context),
        external_styles=css,
        allow_loading_external_files=True,
    ).transform()
    msg.attach_alternative(html, "text/html")
    msg.send()

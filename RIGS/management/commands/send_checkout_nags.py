import datetime

import premailer
from django.conf import settings
from django.contrib.staticfiles import finders
from django.core.mail import EmailMultiAlternatives
from django.core.management.base import BaseCommand
from django.template.loader import get_template
from django.urls import reverse
from django.utils import timezone

from RIGS import models

NAG_AFTER_HOURS = 36


class Command(BaseCommand):
    help = "Emails people who have been checked in to a rig for too long. Triggered daily at 5pm through sys cron in production."

    def handle(self, *args, **options):
        cutoff = timezone.now() - datetime.timedelta(hours=NAG_AFTER_HOURS)
        checkins = models.EventCheckIn.objects.filter(end_time__isnull=True, time__lte=cutoff).select_related("person", "event").order_by("time")
        by_person = {}
        for checkin in checkins:
            by_person.setdefault(checkin.person, []).append(
                {"checkin": checkin, "url": "https://" + settings.DOMAIN + reverse("checkin_checkout", kwargs={"pk": checkin.pk})}
            )
        css = finders.find("css/email.css")
        for person, items in by_person.items():
            if not person.email:
                continue
            context = {"user": person, "checkins": items, "hours": NAG_AFTER_HOURS}
            msg = EmailMultiAlternatives(
                "You are still checked in to a rig",
                get_template("email/checkout_nag.txt").render(context),
                to=[person.email],
                reply_to=[f"h.s.manager@{settings.DOMAIN}"],
            )
            html = premailer.Premailer(
                get_template("email/checkout_nag.html").render(context),
                external_styles=css,
                allow_loading_external_files=True,
            ).transform()
            msg.attach_alternative(html, "text/html")
            msg.send()

import premailer
import datetime

from django.template.loader import get_template
from django.contrib.staticfiles import finders
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone
from django.urls import reverse

from RIGS import models


class Command(BaseCommand):
    help = 'Sends email reminders as required. Triggered daily through heroku-scheduler in production.'

    def handle(self, *args, **options):
        events = models.Event.objects.current_events().select_related('riskassessment')
        for event in events:
            earliest_time = event.earliest_time if isinstance(event.earliest_time, datetime.datetime) else timezone.make_aware(datetime.datetime.combine(event.earliest_time, datetime.time(00, 00)))
            # 48 hours = 172800 seconds
            if event.is_rig and not event.cancelled and not event.dry_hire and (earliest_time - timezone.now()).total_seconds() <= 172800 and not hasattr(event, 'riskassessment'):
                context = {
                    "event": event,
                    "url": "https://" + settings.DOMAIN + reverse('event_ra', kwargs={'pk': event.pk})
                }
                target = event.mic.email if event.mic else f"productions@{settings.DOMAIN}"
                msg = EmailMultiAlternatives(
                    f"{event} - Risk Assessment Incomplete",
                    get_template("email/ra_reminder.txt").render(context),
                    to=[target],
                    reply_to=[f"h.s.manager@{settings.DOMAIN}"],
                )
                css = finders.find('css/email.css')
                html = premailer.Premailer(get_template("email/ra_reminder.html").render(context), external_styles=css).transform()
                msg.attach_alternative(html, 'text/html')
                msg.send()

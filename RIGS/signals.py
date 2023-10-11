import re
import urllib.error
import urllib.parse
import urllib.request
from io import BytesIO
import datetime

from PyPDF2 import PdfFileReader, PdfFileMerger
from django.conf import settings
from django.contrib.staticfiles import finders
from django.core.cache import cache
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.db.models.signals import post_save
from django.template.loader import get_template
from django.urls import reverse
from django.utils import timezone
from premailer import Premailer
from registration.signals import user_activated
from reversion import revisions as reversion
from z3c.rml import rml2pdf

from RIGS import models


def send_eventauthorisation_success_email(instance):
    # Generate PDF first to prevent context conflicts
    context = {
        'object': instance.event,
        'receipt': True,
        'current_user': False,
    }

    template = get_template('event_print.xml')
    merger = PdfFileMerger()

    rml = template.render(context)

    buffer = rml2pdf.parseString(rml)
    merger.append(PdfFileReader(buffer))
    buffer.close()

    terms = urllib.request.urlopen(settings.TERMS_OF_HIRE_URL)
    merger.append(BytesIO(terms.read()))

    merged = BytesIO()
    merger.write(merged)

    # Produce email content
    context = {
        'object': instance,
    }

    if instance.event.person is not None and instance.email == instance.event.person.email:
        context['to_name'] = instance.event.person.name
    elif instance.event.organisation is not None and instance.email == instance.event.organisation.email:
        context['to_name'] = instance.event.organisation.name

    subject = f"{instance.event.display_id} | {instance.event.name} - Event Authorised"

    client_email = EmailMultiAlternatives(
        subject,
        get_template("email/eventauthorisation_client_success.txt").render(context),
        to=[instance.email],
        reply_to=[settings.AUTHORISATION_NOTIFICATION_ADDRESS],
    )

    css = finders.find('css/email.css')
    html = Premailer(get_template("email/eventauthorisation_client_success.html").render(context),
                     external_styles=css).transform()
    client_email.attach_alternative(html, 'text/html')

    escapedEventName = re.sub(r'[^a-zA-Z0-9 \n\.]', '', instance.event.name)

    client_email.attach(f'{instance.event.display_id} - {escapedEventName} - CONFIRMATION.pdf',
                        merged.getvalue(),
                        'application/pdf'
                        )

    if instance.event.mic:
        mic_email_address = instance.event.mic.email
    else:
        mic_email_address = settings.AUTHORISATION_NOTIFICATION_ADDRESS

    mic_email = EmailMessage(
        subject,
        get_template("email/eventauthorisation_mic_success.txt").render(context),
        to=[mic_email_address]
    )

    # Now we have both emails successfully generated, send them out
    client_email.send(fail_silently=True)
    mic_email.send(fail_silently=True)

    # Set event to booked now that it's authorised
    instance.event.status = models.Event.BOOKED
    instance.event.save()


def on_revision_commit(sender, instance, created, **kwargs):
    if created:
        send_eventauthorisation_success_email(instance)


post_save.connect(on_revision_commit, sender=models.EventAuthorisation)


def send_admin_awaiting_approval_email(user, request, **kwargs):
    # Bit more controlled than just emailing all superusers
    for admin in models.Profile.admins():
        # Check we've ever emailed them before and if so, if cooldown has passed.
        if admin.last_emailed is None or admin.last_emailed + settings.EMAIL_COOLDOWN <= timezone.now():
            context = {
                'request': request,
                'link_suffix': reverse("admin:RIGS_profile_changelist") + f'?is_approved__exact=0&date_joined__date={timezone.now().date()}',
                'number_of_users': models.Profile.users_awaiting_approval_count(),
                'to_name': admin.first_name
            }

            email = EmailMultiAlternatives(
                f"{context['number_of_users']} new users awaiting approval on RIGS",
                get_template("email/admin_awaiting_approval.txt").render(context),
                to=[admin.email],
                reply_to=[user.email],
            )
            css = finders.find('css/email.css')
            html = Premailer(get_template("email/admin_awaiting_approval.html").render(context),
                             external_styles=css).transform()
            email.attach_alternative(html, 'text/html')
            email.send()

            # Update last sent
            admin.last_emailed = timezone.now()
            admin.save()


user_activated.connect(send_admin_awaiting_approval_email)


def update_cache(sender, instance, created, **kwargs):
    cache.clear()


for model in reversion.get_registered_models():
    post_save.connect(update_cache, sender=model)

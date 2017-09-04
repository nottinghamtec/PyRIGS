import re
import urllib.request, urllib.error, urllib.parse
from io import BytesIO

from django.db.models.signals import post_save
from PyPDF2 import PdfFileReader, PdfFileMerger
from django.conf import settings
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.template.loader import get_template
from premailer import Premailer
from z3c.rml import rml2pdf

from RIGS import models


def send_eventauthorisation_success_email(instance):
    # Generate PDF first to prevent context conflicts
    context = {
        'object': instance.event,
        'fonts': {
            'opensans': {
                'regular': 'RIGS/static/fonts/OPENSANS-REGULAR.TTF',
                'bold': 'RIGS/static/fonts/OPENSANS-BOLD.TTF',
            }
        },
        'receipt': True,
        'current_user': False,
    }

    template = get_template('RIGS/event_print.xml')
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

    if instance.email == instance.event.person.email:
        context['to_name'] = instance.event.person.name

    subject = "N%05d | %s - Event Authorised" % (instance.event.pk, instance.event.name)

    client_email = EmailMultiAlternatives(
        subject,
        get_template("RIGS/eventauthorisation_client_success.txt").render(context),
        to=[instance.email],
        reply_to=[settings.AUTHORISATION_NOTIFICATION_ADDRESS],
    )

    css = staticfiles_storage.path('css/email.css')
    html = Premailer(get_template("RIGS/eventauthorisation_client_success.html").render(context),
                               external_styles=css).transform()
    client_email.attach_alternative(html, 'text/html')

    escapedEventName = re.sub('[^a-zA-Z0-9 \n\.]', '', instance.event.name)

    client_email.attach('N%05d - %s - CONFIRMATION.pdf' % (instance.event.pk, escapedEventName),
                        merged.getvalue(),
                        'application/pdf'
                        )

    if instance.event.mic:
        mic_email_address = instance.event.mic.email
    else:
        mic_email_address = settings.AUTHORISATION_NOTIFICATION_ADDRESS

    mic_email = EmailMessage(
        subject,
        get_template("RIGS/eventauthorisation_mic_success.txt").render(context),
        to=[mic_email_address]
    )

    # Now we have both emails successfully generated, send them out
    client_email.send(fail_silently=True)
    mic_email.send(fail_silently=True)


def on_revision_commit(sender, instance, created, **kwargs):
    if created:
        send_eventauthorisation_success_email(instance)


post_save.connect(on_revision_commit, sender=models.EventAuthorisation)

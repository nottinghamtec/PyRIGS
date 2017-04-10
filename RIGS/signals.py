import reversion
from django.conf import settings

from django.core.mail import EmailMessage
from django.template.loader import get_template

from RIGS import models


def send_eventauthorisation_success_email(instance):
    context = {
        'object': instance,
    }
    client_email = EmailMessage(
        "N%05d | %s - Event Authorised".format(instance.event.pk, instance.event.name),
        get_template("RIGS/eventauthorisation_client_success.txt").render(context),
        to=[instance.email]
    )

    if instance.event.mic:
        mic_email_address = instance.event.mic.email
    else:
        mic_email_address = settings.AUTHORISATION_NOTIFICATION_ADDRESS

    mic_email = EmailMessage(
        "N%05d | %s - Event Authorised".format(instance.event.pk, instance.event.name),
        get_template("RIGS/eventauthorisation_mic_success.txt").render(context),
        to=[mic_email_address]
    )

    client_email.send()
    mic_email.send()


def on_revision_commit(instances, **kwargs):
    for instance in instances:
        if isinstance(instance, models.EventAuthorisation):
            send_eventauthorisation_success_email(instance)


reversion.post_revision_commit.connect(on_revision_commit)

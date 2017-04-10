import reversion

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
    mic_email = EmailMessage(
        "N%05d | %s - Event Authorised".format(instance.event.pk, instance.event.name),
        get_template("RIGS/eventauthorisation_mic_success.txt").render(context),
        to=[instance.event.mic.email]
    )

    client_email.send()
    mic_email.send()


def on_revision_commit(instances, **kwargs):
    for instance in instances:
        if isinstance(instance, models.EventAuthorisation):
            send_eventauthorisation_success_email(instance)


reversion.post_revision_commit.connect(on_revision_commit)

import functools
import logging

from django.db import transaction
from django.db.models.signals import post_save, pre_save

from notifications import triggers

logger = logging.getLogger(__name__)


def safely(handler):
    @functools.wraps(handler)
    def wrapper(*args, **kwargs):
        try:
            with transaction.atomic():
                handler(*args, **kwargs)
        except Exception:
            logger.exception("Couldn't queue notifications in %s", handler.__name__)

    return wrapper


def remember_event(sender, instance, raw=False, **kwargs):
    if raw:
        return
    try:
        instance._notify_old = triggers.snapshot_event(instance)
    except Exception:
        logger.exception("Couldn't read the previous state of event %s", instance.pk)
        instance._notify_old = None
        instance._notify_skip = True


@safely
def event_saved(sender, instance, raw=False, **kwargs):
    if raw or getattr(instance, "_notify_skip", False):
        return
    old = instance.__dict__.pop("_notify_old", None)
    triggers.event_saved(instance, old)


@safely
def qualification_saved(sender, instance, created, raw=False, **kwargs):
    if raw:
        return
    if created:
        triggers.training_logged(instance)
    triggers.levels_ready(instance)


def connect():
    from RIGS.models import Event
    from training.models import TrainingItemQualification

    pre_save.connect(remember_event, sender=Event, dispatch_uid="notifications_remember_event")
    post_save.connect(event_saved, sender=Event, dispatch_uid="notifications_event_saved")
    post_save.connect(
        qualification_saved, sender=TrainingItemQualification, dispatch_uid="notifications_qualification_saved"
    )


connect()

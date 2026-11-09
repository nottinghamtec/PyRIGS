from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from reversion import revisions as reversion

from notifications.dispatch import notify

TRACKED_EVENT_FIELDS = (
    "status",
    "start_date",
    "end_date",
    "start_time",
    "end_time",
    "venue_id",
    "meet_at",
    "access_at",
    "mic_id",
)


def acting_user():
    if reversion.is_active():
        return reversion.get_user()
    return None


def group_members(name):
    return get_user_model().objects.filter(groups__name=name, is_active=True).distinct()


def local(value):
    return timezone.localtime(value) if timezone.is_aware(value) else value


def snapshot_event(event):
    if event.pk is None:
        return None
    return type(event).objects.filter(pk=event.pk).values(*TRACKED_EVENT_FIELDS).first()


def describe_event_changes(old, event):
    from RIGS.models import Event

    if old["status"] != Event.CANCELLED and event.status == Event.CANCELLED:
        return "cancelled", ["It has been cancelled"]
    changes = []
    if old["status"] == Event.CANCELLED and event.status != Event.CANCELLED:
        changes.append("it is no longer cancelled")
    if old["start_date"] != event.start_date or old["end_date"] != event.end_date:
        changes.append(f"date is now {event.start_date:%a %d %b}")
    if old["start_time"] != event.start_time or old["end_time"] != event.end_time:
        changes.append("start or end time changed")
    if old["venue_id"] != event.venue_id:
        changes.append(f"venue is now {event.venue or 'not set'}")
    if old["meet_at"] != event.meet_at:
        changes.append(f"meet is now {local(event.meet_at):%a %d %b %H:%M}" if event.meet_at else "meet time removed")
    if old["access_at"] != event.access_at:
        changes.append(
            f"access is now {local(event.access_at):%a %d %b %H:%M}" if event.access_at else "access time removed"
        )
    return "changed", changes


def event_saved(event, old):
    from RIGS.models import Profile

    created = old is None
    actor = acting_user()
    old_mic_id = old["mic_id"] if old else None
    url = event.get_absolute_url()

    if event.mic_id and event.mic_id != old_mic_id and event.mic != actor:
        notify(
            event.mic,
            "mic_assigned",
            f"You're MIC on {event.display_id}",
            f"{event.name}, {event.start_date:%a %d %b}",
            url=url,
            tag=f"mic-{event.pk}",
        )
    if old_mic_id and old_mic_id != event.mic_id:
        previous = Profile.objects.filter(pk=old_mic_id).first()
        if previous is not None and previous != actor:
            notify(
                previous,
                "mic_assigned",
                f"You're no longer MIC on {event.display_id}",
                event.name,
                url=url,
                tag=f"mic-{event.pk}",
            )

    if created or event.mic is None or event.mic == actor or old_mic_id != event.mic_id:
        return
    verb, changes = describe_event_changes(old, event)
    if changes:
        title = f"{event.display_id} {event.name} was {verb}" if verb == "cancelled" else f"{event.display_id} changed"
        notify(
            event.mic,
            "rig_changed",
            title,
            "; ".join(changes),
            url=url,
            tag=f"event-{event.pk}",
            coalesce=True,
        )


def auth_completed(authorisation, client_delivered):
    event = authorisation.event
    recipients = [authorisation.sent_by, event.mic]
    notify(
        recipients,
        "auth_completed",
        f"{event.display_id} authorised",
        f"{event.name} has been authorised by the client",
        url=event.get_absolute_url(),
        tag=f"auth-{event.pk}",
        dedupe_key=f"auth-completed:{authorisation.pk}",
        send_email=False,
    )
    if not client_delivered:
        auth_bounced(event, authorisation.sent_by, authorisation.email, "confirmation")


def auth_bounced(event, sender, address, what="request"):
    notify(
        sender,
        "auth_bounced",
        f"{event.display_id} authorisation {what} not delivered",
        f"We couldn't deliver the authorisation {what} to {address}. Check the address and try again.",
        url=event.get_absolute_url(),
        tag=f"auth-bounce-{event.pk}",
    )


def hs_label(obj):
    return obj._meta.verbose_name


def review_complete(obj, reviewer):
    event = obj.event
    if event.mic is None or event.mic == reviewer:
        return
    notify(
        event.mic,
        "review_complete",
        f"{event.display_id} {hs_label(obj)} reviewed",
        f"Reviewed by {reviewer.first_name or reviewer.username}",
        url=obj.get_absolute_url(),
        tag=f"review-{obj._meta.model_name}-{obj.pk}",
    )


def pat_batch_complete(batch, summary, uploader):
    testers = group_members(settings.NOTIFICATION_PAT_GROUP).exclude(pk=getattr(uploader, "pk", None))
    imported = len(summary.imported) + len(summary.replaced)
    notify(
        testers,
        "pat_batch_complete",
        "PAT upload finished",
        f"{batch.original_filename}: {imported} results imported",
        url=batch.get_absolute_url(),
        tag=f"pat-batch-{batch.pk}",
        dedupe_key=f"pat-batch:{batch.pk}",
    )


def training_logged(qualification):
    trainee = qualification.trainee
    supervisor = qualification.supervisor
    if supervisor is not None and supervisor.pk == trainee.pk:
        return
    who = (supervisor.first_name or supervisor.username) if supervisor else "A trainer"
    notify(
        trainee,
        "training_logged",
        f"{who} logged training for you",
        f"{qualification.get_depth_display()} in {qualification.item}",
        url=reverse("trainee_item_detail", kwargs={"pk": trainee.pk}),
        tag=f"training-{trainee.pk}-{supervisor.pk if supervisor else 0}",
        coalesce=True,
    )


def levels_ready(qualification):
    from training.models import TrainingLevel

    trainee = qualification.trainee
    levels = TrainingLevel.objects.filter(requirements__item=qualification.item).distinct()
    done = set(trainee.level_qualifications.values_list("level_id", flat=True))
    for level in levels:
        if level.pk in done or not level.user_has_requirements(trainee):
            continue
        notify(
            trainee,
            "level_ready",
            f"You meet the requirements for {level}",
            "A supervisor can confirm it",
            url=reverse("trainee_detail", kwargs={"pk": trainee.pk}),
            tag=f"level-{trainee.pk}-{level.pk}",
            dedupe_key=f"level-ready:{trainee.pk}:{level.pk}",
        )

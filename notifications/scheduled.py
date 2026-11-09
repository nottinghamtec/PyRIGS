import datetime

from django.conf import settings
from django.db.models import Exists, OuterRef, Q
from django.urls import reverse
from django.utils import timezone

from notifications.dispatch import notify
from notifications.triggers import group_members, local


def live_rigs():
    from RIGS.models import Event

    return Event.objects.filter(is_rig=True, dry_hire=False).exclude(status=Event.CANCELLED)


def queue_meet_reminders(now=None):
    now = now or timezone.now()
    window = now + datetime.timedelta(hours=settings.NOTIFICATION_MEET_REMINDER_HOURS)
    events = live_rigs().filter(meet_at__gt=now, meet_at__lte=window, mic__isnull=False).select_related("mic", "venue")
    queued = []
    for event in events:
        lines = [event.name]
        if event.venue:
            lines.append(f"At {event.venue}")
        if event.access_at:
            lines.append(f"Access from {local(event.access_at):%H:%M}")
        if event.parking_and_access:
            lines.append("Parking and access arranged")
        if event.venue and event.venue.notes:
            lines.append(event.venue.notes[:150])
        queued += notify(
            event.mic,
            "meet_reminder",
            f"Meet at {local(event.meet_at):%H:%M} for {event.display_id}",
            ". ".join(lines),
            url=event.get_absolute_url(),
            tag=f"meet-{event.pk}",
            dedupe_key=f"meet-reminder:{event.pk}:{event.meet_at.isoformat()}",
            send_email=False,
        )
    return queued


def queue_missing_checkins(now=None):
    from RIGS.models import EventCheckIn

    now = now or timezone.now()
    due = now - datetime.timedelta(minutes=settings.NOTIFICATION_CHECKIN_NUDGE_MINUTES)
    stale = due - datetime.timedelta(hours=3)
    events = (
        live_rigs()
        .filter(meet_at__lte=due, meet_at__gte=stale, mic__isnull=False)
        .exclude(Exists(EventCheckIn.objects.filter(event=OuterRef("pk"), person=OuterRef("mic"))))
        .select_related("mic")
    )
    queued = []
    for event in events:
        queued += notify(
            event.mic,
            "not_checked_in",
            f"You haven't checked in to {event.display_id}",
            f"The meet time was {local(event.meet_at):%H:%M}",
            url=reverse("event_checkin", kwargs={"pk": event.pk}),
            tag=f"checkin-{event.pk}",
            dedupe_key=f"not-checked-in:{event.pk}:{event.meet_at.isoformat()}",
            send_email=False,
        )
    return queued


def queue_stale_auth_requests(now=None):
    now = now or timezone.now()
    cutoff = now - datetime.timedelta(days=settings.NOTIFICATION_AUTH_NUDGE_DAYS)
    today = timezone.localdate(now)
    events = (
        live_rigs()
        .filter(auth_request_at__lte=cutoff, auth_request_by__isnull=False, authorisation__isnull=True)
        .filter(Q(end_date__gte=today) | Q(end_date__isnull=True, start_date__gte=today))
        .filter(purchase_order="")
        .select_related("auth_request_by")
    )
    queued = []
    for event in events:
        queued += notify(
            event.auth_request_by,
            "auth_pending",
            f"{event.display_id} still needs authorising",
            f"You asked {event.auth_request_to or 'the client'} to authorise it on "
            f"{local(event.auth_request_at):%a %d %b} and they haven't yet",
            url=event.get_absolute_url(),
            tag=f"auth-pending-{event.pk}",
            dedupe_key=f"auth-pending:{event.pk}:{event.auth_request_at.isoformat()}",
            send_email=False,
        )
    return queued


def queue_waiting_invoices(now=None):
    from RIGS.models import Event

    today = timezone.localdate(now)
    since = today - datetime.timedelta(days=settings.NOTIFICATION_INVOICE_WINDOW_DAYS)
    events = (
        Event.objects.waiting_invoices()
        .exclude(status=Event.CANCELLED)
        .filter(
            Q(end_date__lt=today, end_date__gte=since)
            | Q(end_date__isnull=True, start_date__lt=today, start_date__gte=since)
        )
    )
    finance = list(group_members(settings.NOTIFICATION_FINANCE_GROUP))
    queued = []
    for event in events:
        queued += notify(
            finance,
            "invoice_waiting",
            f"{event.display_id} is waiting to be invoiced",
            event.name,
            url=reverse("invoice_waiting"),
            tag="invoice-waiting",
            dedupe_key=f"invoice-waiting:{event.pk}",
            send_email=False,
        )
    return queued


SCANNERS = (queue_meet_reminders, queue_missing_checkins, queue_stale_auth_requests, queue_waiting_invoices)


def queue_all(now=None):
    return {scanner.__name__: len(scanner(now)) for scanner in SCANNERS}

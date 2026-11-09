import logging

from django.conf import settings
from django.core.mail import EmailMessage
from django.utils import timezone

from notifications import push
from notifications.kinds import KINDS
from notifications.models import Notification, NotificationPreference

logger = logging.getLogger(__name__)

MAX_BODY = 500


def preference(user, kind, channel):
    override = NotificationPreference.objects.filter(user=user, kind=kind).first()
    if override is not None:
        return getattr(override, channel)
    return getattr(KINDS[kind], f"default_{channel}")


def can_receive(user):
    return user.is_active and (user.is_approved or user.is_superuser)


def notify(recipients, kind, title, body="", url="", tag="", dedupe_key="", coalesce=False, send_email=True):
    if kind not in KINDS:
        raise KeyError(kind)
    if not hasattr(recipients, "__iter__"):
        recipients = [recipients]
    queued = []
    seen = set()
    for user in recipients:
        if user is None or user.pk in seen or not can_receive(user):
            continue
        seen.add(user.pk)
        if not (preference(user, kind, "push") or (send_email and preference(user, kind, "email"))):
            continue
        if dedupe_key and Notification.objects.filter(recipient=user, dedupe_key=dedupe_key).exists():
            continue
        if coalesce and tag:
            waiting = Notification.objects.filter(recipient=user, kind=kind, tag=tag, delivered_at__isnull=True).first()
            if waiting is not None:
                if body and body not in waiting.body:
                    waiting.body = f"{waiting.body}; {body}"[:MAX_BODY] if waiting.body else body[:MAX_BODY]
                    waiting.save(update_fields=["body"])
                queued.append(waiting)
                continue
        queued.append(
            Notification.objects.create(
                recipient=user,
                kind=kind,
                title=title[:120],
                body=body[:MAX_BODY],
                url=url,
                tag=tag,
                dedupe_key=dedupe_key,
                send_email=send_email,
            )
        )
    return queued


def absolute_url(url):
    return url if url.startswith("http") else f"https://{settings.DOMAIN}{url}"


def deliver(notification):
    user = notification.recipient
    if push.configured() and preference(user, notification.kind, "push"):
        push.send_to_user(
            user,
            {
                "title": notification.title,
                "body": notification.body,
                "url": notification.url or "/notifications/",
                "tag": notification.tag or f"notification-{notification.pk}",
                "id": notification.pk,
            },
        )
    if notification.send_email and user.email and preference(user, notification.kind, "email"):
        text = notification.body
        if notification.url:
            text += f"\n\n{absolute_url(notification.url)}"
        text += f"\n\nYou can change which notifications you get at {absolute_url('/notifications/')}"
        EmailMessage(
            notification.title, text, to=[user.email], reply_to=[settings.AUTHORISATION_NOTIFICATION_ADDRESS]
        ).send()


def deliver_pending():
    delivered = 0
    for notification in (
        Notification.objects.filter(delivered_at__isnull=True).select_related("recipient").order_by("pk")
    ):
        claimed = Notification.objects.filter(pk=notification.pk, delivered_at__isnull=True).update(
            delivered_at=timezone.now()
        )
        if not claimed:
            continue
        try:
            deliver(notification)
        except Exception:
            logger.exception("Couldn't deliver notification %s", notification.pk)
            continue
        delivered += 1
    return delivered

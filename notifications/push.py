import json
import logging

from django.conf import settings
from pywebpush import WebPushException, webpush

logger = logging.getLogger(__name__)

PUSH_TTL_SECONDS = 12 * 60 * 60


def configured():
    return bool(settings.VAPID_PRIVATE_KEY and settings.VAPID_PUBLIC_KEY)


def send_to_user(user, payload):
    if not configured():
        return 0
    sent = 0
    for subscription in user.push_subscriptions.all():
        try:
            webpush(
                subscription_info=subscription.info,
                data=json.dumps(payload),
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={"sub": settings.VAPID_SUBJECT},
                ttl=PUSH_TTL_SECONDS,
                timeout=10,
            )
            sent += 1
        except WebPushException as error:
            status = getattr(error.response, "status_code", None)
            if status in (404, 410):
                subscription.delete()
            else:
                logger.warning("Push to %s failed: %s", subscription, error)
        except Exception:
            logger.exception("Push to %s failed", subscription)
    return sent

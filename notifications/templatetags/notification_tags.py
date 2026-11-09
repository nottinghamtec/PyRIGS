from django import template
from django.conf import settings

from notifications import push

register = template.Library()


@register.simple_tag(takes_context=True)
def unread_notifications(context):
    request = context["request"]
    if not hasattr(request, "_unread_notifications"):
        user = request.user
        request._unread_notifications = (
            user.notifications.filter(read_at__isnull=True).count() if user.is_authenticated else 0
        )
    return request._unread_notifications


@register.inclusion_tag("notifications/push_box.html", takes_context=True)
def push_box(context):
    return {
        "push_available": push.configured(),
        "vapid_public_key": settings.VAPID_PUBLIC_KEY,
        "csrf_token": context.get("csrf_token", ""),
        "user": context["request"].user,
    }

import json

from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.templatetags.static import static
from django.urls import reverse
from django.utils import timezone
from django.views import generic
from django.views.decorators.cache import cache_control, never_cache

from PyRIGS.views import is_ajax
from notifications import push
from notifications.dispatch import preference
from notifications.kinds import KINDS_LIST, visible_to
from notifications.models import Notification, NotificationPreference, PushSubscription

RECENT_LIMIT = 50
TRAY_LIMIT = 15


class NotificationList(generic.TemplateView):
    template_name = "notifications/notification_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context["page_title"] = "Notifications"
        context["notifications"] = user.notifications.all()[:RECENT_LIMIT]
        context["kinds"] = [
            {
                "kind": kind,
                "push": preference(user, kind.slug, "push"),
                "email": preference(user, kind.slug, "email"),
            }
            for kind in KINDS_LIST
            if visible_to(kind, user)
        ]
        context["push_available"] = push.configured()
        context["vapid_public_key"] = settings.VAPID_PUBLIC_KEY
        context["device_count"] = user.push_subscriptions.count()
        return context

    def post(self, request, *args, **kwargs):
        if "mark_read" in request.POST:
            request.user.notifications.filter(read_at__isnull=True).update(read_at=timezone.now())
            messages.success(request, "Marked everything as read")
            return redirect("notification_list")
        for kind in KINDS_LIST:
            if not visible_to(kind, request.user):
                continue
            NotificationPreference.objects.update_or_create(
                user=request.user,
                kind=kind.slug,
                defaults={
                    "push": f"push_{kind.slug}" in request.POST,
                    "email": kind.email_configurable and f"email_{kind.slug}" in request.POST,
                },
            )
        messages.success(request, "Notification preferences saved")
        return redirect("notification_list")


class NotificationTray(generic.TemplateView):
    template_name = "notifications/tray.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["notifications"] = self.request.user.notifications.all()[:TRAY_LIMIT]
        context["unread"] = self.request.user.notifications.filter(read_at__isnull=True).count()
        return context

    def get(self, request, *args, **kwargs):
        if not is_ajax(request):
            return redirect("notification_list")
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        request.user.notifications.filter(read_at__isnull=True).update(read_at=timezone.now())
        request._unread_notifications = 0
        return super().get(request, *args, **kwargs)


class OpenNotification(generic.View):
    def get(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
        if notification.read_at is None:
            notification.read_at = timezone.now()
            notification.save(update_fields=["read_at"])
        return redirect(notification.url or reverse("notification_list"))


def read_json(request):
    try:
        return json.loads(request.body)
    except ValueError:
        return None


class Subscribe(generic.View):
    def post(self, request):
        data = read_json(request)
        try:
            endpoint = data["endpoint"]
            keys = data["keys"]
            p256dh, auth = keys["p256dh"], keys["auth"]
        except TypeError, KeyError:
            return HttpResponseBadRequest("Not a push subscription")
        PushSubscription.objects.update_or_create(
            endpoint=endpoint,
            defaults={
                "user": request.user,
                "p256dh": p256dh,
                "auth": auth,
                "user_agent": request.META.get("HTTP_USER_AGENT", "")[:255],
            },
        )
        return JsonResponse({"subscribed": True})


class Unsubscribe(generic.View):
    def post(self, request):
        data = read_json(request)
        if not isinstance(data, dict) or "endpoint" not in data:
            return HttpResponseBadRequest("Not a push subscription")
        request.user.push_subscriptions.filter(endpoint=data["endpoint"]).delete()
        return JsonResponse({"subscribed": False})


class CheckSubscription(generic.View):
    def post(self, request):
        data = read_json(request)
        if not isinstance(data, dict) or "endpoint" not in data:
            return HttpResponseBadRequest("Not a push subscription")
        known = request.user.push_subscriptions.filter(endpoint=data["endpoint"]).exists()
        return JsonResponse({"known": known})


class SendTest(generic.View):
    def post(self, request):
        sent = push.send_to_user(
            request.user,
            {
                "title": "RIGS notifications work",
                "body": "This device is set up.",
                "url": "/notifications/",
                "tag": "test",
            },
        )
        return JsonResponse({"sent": sent})


@cache_control(public=True, max_age=300)
def push_client(request):
    return render(request, "notifications/push.js", content_type="text/javascript")


@never_cache
def service_worker(request):
    response = render(request, "notifications/sw.js", content_type="text/javascript")
    response["Service-Worker-Allowed"] = "/"
    return response


@never_cache
def manifest(request):
    data = {
        "name": "Rig Information Gathering System",
        "short_name": "RIGS",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "theme_color": "#3853a4",
        "background_color": "#ffffff",
        "icons": [{"src": static("imgs/pyrigs-avatar.png"), "sizes": "128x128", "type": "image/png"}],
    }
    return HttpResponse(json.dumps(data), content_type="application/manifest+json")

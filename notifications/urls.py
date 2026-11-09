from django.contrib.auth.decorators import login_required
from django.urls import path

from notifications import views

urlpatterns = [
    path("notifications/", login_required(views.NotificationList.as_view()), name="notification_list"),
    path("notifications/tray/", login_required(views.NotificationTray.as_view()), name="notification_tray"),
    path("notifications/<int:pk>/open/", login_required(views.OpenNotification.as_view()), name="notification_open"),
    path("notifications/subscribe/", login_required(views.Subscribe.as_view()), name="push_subscribe"),
    path("notifications/unsubscribe/", login_required(views.Unsubscribe.as_view()), name="push_unsubscribe"),
    path("notifications/check/", login_required(views.CheckSubscription.as_view()), name="push_check"),
    path("notifications/test/", login_required(views.SendTest.as_view()), name="push_test"),
    path("notifications/push.js", views.push_client, name="push_client"),
    path("sw.js", views.service_worker, name="service_worker"),
    path("manifest.webmanifest", views.manifest, name="web_manifest"),
]

import json
from unittest import mock

import pytest
from django.urls import reverse

from notifications.models import Notification, NotificationPreference, PushSubscription

pytestmark = pytest.mark.django_db

SUBSCRIPTION = {"endpoint": "https://push.example/abc", "keys": {"p256dh": "key", "auth": "secret"}}


def post_json(client, url, data):
    return client.post(url, json.dumps(data), content_type="application/json")


@pytest.fixture
def user_client(client, mic):
    client.force_login(mic)
    return client


def test_pages_require_login(client):
    for name in ("notification_list", "push_subscribe", "push_unsubscribe", "push_test"):
        assert client.get(reverse(name)).status_code == 302


def test_service_worker_and_manifest_are_public(client):
    response = client.get(reverse("service_worker"))
    assert response.status_code == 200
    assert response["Service-Worker-Allowed"] == "/"
    assert "javascript" in response["Content-Type"]
    assert b"showNotification" in response.content
    manifest = client.get(reverse("web_manifest"))
    assert manifest.status_code == 200
    assert json.loads(manifest.content)["display"] == "standalone"


def test_manifest_is_linked_from_pages(user_client):
    assert reverse("web_manifest") in user_client.get(reverse("notification_list")).content.decode()


def test_subscribe_and_unsubscribe(user_client, mic):
    assert post_json(user_client, reverse("push_subscribe"), SUBSCRIPTION).status_code == 200
    subscription = PushSubscription.objects.get()
    assert subscription.user == mic and subscription.p256dh == "key"
    post_json(user_client, reverse("push_subscribe"), {**SUBSCRIPTION, "keys": {"p256dh": "new", "auth": "secret"}})
    assert PushSubscription.objects.get().p256dh == "new"
    assert (
        post_json(user_client, reverse("push_unsubscribe"), {"endpoint": SUBSCRIPTION["endpoint"]}).status_code == 200
    )
    assert not PushSubscription.objects.exists()


def test_subscribe_rejects_junk(user_client):
    assert post_json(user_client, reverse("push_subscribe"), {"endpoint": "x"}).status_code == 400
    assert user_client.post(reverse("push_subscribe"), "not json", content_type="application/json").status_code == 400


def test_cannot_unsubscribe_someone_else(user_client, other):
    PushSubscription.objects.create(user=other, endpoint="https://push.example/theirs", p256dh="p", auth="a")
    post_json(user_client, reverse("push_unsubscribe"), {"endpoint": "https://push.example/theirs"})
    assert PushSubscription.objects.count() == 1


def test_send_test(user_client, mic, push_settings):
    PushSubscription.objects.create(user=mic, endpoint="https://push.example/1", p256dh="p", auth="a")
    with mock.patch("notifications.push.webpush") as webpush:
        response = user_client.post(reverse("push_test"))
    assert response.json() == {"sent": 1}
    webpush.assert_called_once()


def test_list_shows_notifications_and_marks_read(user_client, mic, other):
    mine = Notification.objects.create(recipient=mic, kind="rig_changed", title="Mine", url="/event/1/")
    Notification.objects.create(recipient=other, kind="rig_changed", title="Theirs")
    response = user_client.get(reverse("notification_list"))
    assert "Mine" in response.content.decode() and "Theirs" not in response.content.decode()
    opened = user_client.get(reverse("notification_open", kwargs={"pk": mine.pk}))
    assert opened.status_code == 302 and opened.url == "/event/1/"
    mine.refresh_from_db()
    assert mine.read_at is not None


def test_cannot_open_someone_elses(user_client, other):
    theirs = Notification.objects.create(recipient=other, kind="rig_changed", title="Theirs")
    assert user_client.get(reverse("notification_open", kwargs={"pk": theirs.pk})).status_code == 404


def test_mark_all_read(user_client, mic):
    Notification.objects.create(recipient=mic, kind="rig_changed", title="One")
    user_client.post(reverse("notification_list"), {"mark_read": "1"})
    assert not Notification.objects.filter(read_at__isnull=True).exists()


def test_unread_count_shows_in_menu(user_client, mic):
    Notification.objects.create(recipient=mic, kind="rig_changed", title="One")
    Notification.objects.create(recipient=mic, kind="rig_changed", title="Two")
    assert 'text-bg-danger rounded-pill">2<' in user_client.get(reverse("notification_list")).content.decode()


def test_save_preferences(user_client, mic):
    user_client.post(reverse("notification_list"), {"push_rig_changed": "on", "email_meet_reminder": "on"})
    changed = NotificationPreference.objects.get(user=mic, kind="rig_changed")
    assert changed.push and not changed.email
    reminder = NotificationPreference.objects.get(user=mic, kind="meet_reminder")
    assert reminder.email and not reminder.push
    badge = NotificationPreference.objects.get(user=mic, kind="badge_earned")
    assert not badge.email


def test_page_reflects_push_availability(user_client, settings):
    settings.VAPID_PRIVATE_KEY = settings.VAPID_PUBLIC_KEY = ""
    assert "aren't switched on" in user_client.get(reverse("notification_list")).content.decode()
    settings.VAPID_PRIVATE_KEY, settings.VAPID_PUBLIC_KEY = "a", "b"
    assert 'id="push-panel"' in user_client.get(reverse("notification_list")).content.decode()


def listed(client):
    return {row["kind"].slug for row in client.get(reverse("notification_list")).context["kinds"]}


def test_group_only_categories_are_hidden_from_everyone_else(user_client, mic, settings):
    from django.contrib.auth.models import Group

    assert listed(user_client).isdisjoint({"invoice_waiting", "pat_batch_complete", "admin_approval"})
    mic.groups.add(Group.objects.create(name="Finance"))
    assert "invoice_waiting" in listed(user_client)
    mic.groups.add(Group.objects.create(name="PAT Testers"))
    assert "pat_batch_complete" in listed(user_client)
    settings.ADMINS = [("IT", mic.email)]
    assert "admin_approval" in listed(user_client)


def test_saving_does_not_create_preferences_for_hidden_categories(user_client, mic):
    user_client.post(reverse("notification_list"), {"push_invoice_waiting": "on"})
    assert not NotificationPreference.objects.filter(user=mic, kind="invoice_waiting").exists()
    assert NotificationPreference.objects.filter(user=mic, kind="rig_changed").exists()


def test_check_reports_whether_server_knows_this_device(user_client, mic, other):
    url = reverse("push_check")
    PushSubscription.objects.create(user=mic, endpoint="https://push.example/mine", p256dh="p", auth="a")
    PushSubscription.objects.create(user=other, endpoint="https://push.example/theirs", p256dh="p", auth="a")
    assert post_json(user_client, url, {"endpoint": "https://push.example/mine"}).json() == {"known": True}
    assert post_json(user_client, url, {"endpoint": "https://push.example/gone"}).json() == {"known": False}
    assert post_json(user_client, url, {"endpoint": "https://push.example/theirs"}).json() == {"known": False}
    assert post_json(user_client, url, {"nope": 1}).status_code == 400


def test_check_requires_login(client):
    assert client.post(reverse("push_check"), "{}", content_type="application/json").status_code == 302


def test_resubscribing_a_device_moves_it_to_the_current_user(user_client, mic, other):
    PushSubscription.objects.create(user=other, endpoint=SUBSCRIPTION["endpoint"], p256dh="p", auth="a")
    post_json(user_client, reverse("push_subscribe"), SUBSCRIPTION)
    assert PushSubscription.objects.get().user == mic


def test_push_client_script_is_served(client):
    response = client.get(reverse("push_client"))
    assert response.status_code == 200
    assert "javascript" in response["Content-Type"]
    assert b"window.RigsPush" in response.content


def test_home_page_has_notifications_box_above_quick_links(user_client, push_settings):
    page = user_client.get(reverse("index")).content.decode()
    assert 'id="push-box"' in page
    assert f'data-key="{push_settings.VAPID_PUBLIC_KEY}"' in page
    assert f'data-user="{user_client.session["_auth_user_id"]}"' in page
    assert page.index('id="push-box"') < page.index("Quick Links")
    assert "data-push-dismiss" in page


def test_home_page_has_no_box_when_push_is_not_configured(user_client, settings):
    settings.VAPID_PRIVATE_KEY = settings.VAPID_PUBLIC_KEY = ""
    page = user_client.get(reverse("index")).content.decode()
    assert 'id="push-box"' not in page
    assert "Quick Links" in page


def test_unread_count_is_in_the_navbar_and_nowhere_when_zero(user_client, mic):
    page = user_client.get(reverse("index")).content.decode()
    assert 'id="navbar-unread"' not in page
    Notification.objects.create(recipient=mic, kind="rig_changed", title="One")
    Notification.objects.create(recipient=mic, kind="rig_changed", title="Two")
    page = user_client.get(reverse("index")).content.decode()
    assert 'id="navbar-unread"' in page
    assert "2 unread notifications" in page


def test_navbar_count_is_capped(user_client, mic):
    Notification.objects.bulk_create(Notification(recipient=mic, kind="rig_changed", title=str(n)) for n in range(120))
    page = user_client.get(reverse("index")).content.decode()
    assert ">99+<" in page


AJAX = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}


def test_bell_opens_the_tray_overlay(user_client):
    page = user_client.get(reverse("index")).content.decode()
    assert 'id="notification-bell"' in page
    assert 'data-bs-toggle="offcanvas" data-bs-target="#notification-tray"' in page
    assert 'id="notification-tray"' in page and 'class="offcanvas offcanvas-end"' in page
    assert page.index('id="notification-bell"') < page.index('id="user"')


def test_tray_is_not_on_pages_for_signed_out_users(client):
    assert 'id="notification-tray"' not in client.get(reverse("login")).content.decode()


def test_tray_lists_recent_notifications_as_a_fragment(user_client, mic, other):
    Notification.objects.create(recipient=mic, kind="rig_changed", title="Mine", body="Date changed", url="/event/1/")
    Notification.objects.create(recipient=other, kind="rig_changed", title="Theirs")
    response = user_client.get(reverse("notification_tray"), **AJAX)
    content = response.content.decode()
    assert response.status_code == 200
    assert "Mine" in content and "Date changed" in content and "Theirs" not in content
    assert "<html" not in content and "modal-dialog" not in content
    assert "Mark all read" in content


def test_tray_without_ajax_goes_to_the_full_page(user_client):
    assert user_client.get(reverse("notification_tray")).url == reverse("notification_list")


def test_tray_is_limited_and_empty_state(user_client, mic):
    assert "Nothing yet" in user_client.get(reverse("notification_tray"), **AJAX).content.decode()
    for number in range(20):
        Notification.objects.create(recipient=mic, kind="rig_changed", title=f"Item {number}")
    content = user_client.get(reverse("notification_tray"), **AJAX).content.decode()
    assert content.count("list-group-item ") == 15


def test_tray_mark_all_read_returns_the_refreshed_tray(user_client, mic):
    Notification.objects.create(recipient=mic, kind="rig_changed", title="One")
    response = user_client.post(reverse("notification_tray"), **AJAX)
    assert response.status_code == 200
    assert not Notification.objects.filter(read_at__isnull=True).exists()
    assert "Mark all read" not in response.content.decode()


def test_tray_requires_login(client):
    assert client.get(reverse("notification_tray")).status_code == 302


def test_navbar_count_costs_one_query_however_many_places_show_it(user_client, mic):
    Notification.objects.create(recipient=mic, kind="rig_changed", title="One")
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    with CaptureQueriesContext(connection) as queries:
        user_client.get(reverse("notification_list"))
    assert sum("notifications_notification" in q["sql"] and "COUNT" in q["sql"] for q in queries) == 1


def test_stylesheet_includes_the_bootstrap_offcanvas_the_tray_needs(settings):
    scss = (settings.BASE_DIR / "pipeline/source_assets/scss/screen.scss").read_text()
    assert '@import "node_modules/bootstrap/scss/offcanvas";' in scss


def test_bell_and_user_menu_are_centred_with_the_rest_of_the_navbar(user_client):
    page = user_client.get(reverse("index")).content.decode()
    assert 'class="nav-item align-self-end align-self-lg-center" id="notification-bell"' in page
    assert 'class="nav-item dropdown align-self-end align-self-lg-center" id="user"' in page

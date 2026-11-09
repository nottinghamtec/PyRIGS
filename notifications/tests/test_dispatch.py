from unittest import mock

import pytest
from django.core import mail
from django.utils import timezone
from pywebpush import WebPushException

from notifications import dispatch
from notifications.models import Notification, NotificationPreference, PushSubscription

pytestmark = pytest.mark.django_db


def test_notify_queues_one_per_recipient(mic, other):
    queued = dispatch.notify([mic, other, mic], "rig_changed", "Title", "Body", url="/x/")
    assert len(queued) == 2
    assert Notification.objects.filter(kind="rig_changed").count() == 2


def test_notify_skips_inactive_and_unapproved(mic, other):
    mic.is_active = False
    mic.save()
    other.is_approved = False
    other.save()
    assert dispatch.notify([mic, other], "rig_changed", "Title") == []


def test_dedupe_key_blocks_repeats_even_after_delivery(mic):
    first = dispatch.notify(mic, "rig_changed", "Title", dedupe_key="a")
    assert len(first) == 1
    dispatch.deliver_pending()
    assert dispatch.notify(mic, "rig_changed", "Title", dedupe_key="a") == []
    assert len(dispatch.notify(mic, "rig_changed", "Title", dedupe_key="b")) == 1


def test_coalesce_merges_into_waiting_notification(mic):
    dispatch.notify(mic, "training_logged", "Logged", "One", tag="t", coalesce=True)
    dispatch.notify(mic, "training_logged", "Logged", "Two", tag="t", coalesce=True)
    dispatch.notify(mic, "training_logged", "Logged", "Two", tag="t", coalesce=True)
    notification = Notification.objects.get()
    assert notification.body == "One; Two"
    dispatch.deliver_pending()
    dispatch.notify(mic, "training_logged", "Logged", "Three", tag="t", coalesce=True)
    assert Notification.objects.count() == 2


def test_muted_kind_is_not_queued(mic):
    NotificationPreference.objects.create(user=mic, kind="rig_changed", push=False, email=False)
    assert dispatch.notify(mic, "rig_changed", "Title") == []


def test_not_checked_in_is_on_by_default_for_push_only(mic):
    assert len(dispatch.notify(mic, "not_checked_in", "Title", send_email=False)) == 1
    dispatch.deliver_pending()
    assert mail.outbox == []


def test_unknown_kind_is_an_error(mic):
    with pytest.raises(KeyError):
        dispatch.notify(mic, "nope", "Title")


def subscribe(user, endpoint="https://push.example/1"):
    return PushSubscription.objects.create(user=user, endpoint=endpoint, p256dh="p", auth="a")


def test_deliver_pushes_to_every_device(push_settings, mic):
    subscribe(mic, "https://push.example/1")
    subscribe(mic, "https://push.example/2")
    dispatch.notify(mic, "rig_changed", "Moved", "Date changed", url="/event/1/", tag="event-1", send_email=False)
    with mock.patch("notifications.push.webpush") as webpush:
        assert dispatch.deliver_pending() == 1
    assert webpush.call_count == 2
    payload = webpush.call_args.kwargs["data"]
    assert '"title": "Moved"' in payload and '"url": "/event/1/"' in payload
    assert Notification.objects.get().delivered_at is not None
    with mock.patch("notifications.push.webpush") as webpush:
        assert dispatch.deliver_pending() == 0
    webpush.assert_not_called()


def test_push_respects_preference(push_settings, mic):
    subscribe(mic)
    NotificationPreference.objects.create(user=mic, kind="rig_changed", push=False, email=True)
    dispatch.notify(mic, "rig_changed", "Moved", send_email=False)
    with mock.patch("notifications.push.webpush") as webpush:
        dispatch.deliver_pending()
    webpush.assert_not_called()


def test_no_push_without_vapid_keys(settings, mic):
    settings.VAPID_PRIVATE_KEY = ""
    subscribe(mic)
    dispatch.notify(mic, "rig_changed", "Moved", send_email=False)
    with mock.patch("notifications.push.webpush") as webpush:
        dispatch.deliver_pending()
    webpush.assert_not_called()


def test_dead_subscription_is_removed(push_settings, mic):
    subscribe(mic, "https://push.example/gone")
    subscribe(mic, "https://push.example/ok")

    def fake(subscription_info, **kwargs):
        if subscription_info["endpoint"].endswith("gone"):
            raise WebPushException("gone", response=mock.Mock(status_code=410))

    dispatch.notify(mic, "rig_changed", "Moved", send_email=False)
    with mock.patch("notifications.push.webpush", side_effect=fake):
        dispatch.deliver_pending()
    assert list(PushSubscription.objects.values_list("endpoint", flat=True)) == ["https://push.example/ok"]


def test_transient_push_failure_keeps_subscription(push_settings, mic):
    subscribe(mic)
    dispatch.notify(mic, "rig_changed", "Moved", send_email=False)
    with mock.patch(
        "notifications.push.webpush", side_effect=WebPushException("down", response=mock.Mock(status_code=500))
    ):
        dispatch.deliver_pending()
    assert PushSubscription.objects.count() == 1


def test_email_channel(mic):
    dispatch.notify(mic, "rig_changed", "Moved", "Date changed", url="/event/1/")
    dispatch.deliver_pending()
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [mic.email]
    assert "Date changed" in mail.outbox[0].body and "/event/1/" in mail.outbox[0].body


def test_email_off_by_default_for_new_kinds(mic):
    dispatch.notify(mic, "meet_reminder", "Meet", "Soon")
    dispatch.deliver_pending()
    assert mail.outbox == []


def test_overlapping_runs_do_not_double_send(mic):
    notification = dispatch.notify(mic, "rig_changed", "Moved")[0]
    Notification.objects.filter(pk=notification.pk).update(delivered_at=timezone.now())
    assert dispatch.deliver_pending() == 0
    assert mail.outbox == []

import datetime

import pytest
from django.core.management import call_command
from django.utils import timezone

from notifications import scheduled
from notifications.models import Notification
from notifications.tests.conftest import make_user
from RIGS.models import Event, EventCheckIn, Invoice, Venue

pytestmark = pytest.mark.django_db


def clear():
    Notification.objects.all().delete()


def test_meet_reminder_two_hours_before(event, mic):
    now = timezone.now()
    event.meet_at = now + datetime.timedelta(hours=1, minutes=30)
    event.venue = Venue.objects.create(name="The Hall", notes="Use the side door")
    event.save()
    clear()
    assert len(scheduled.queue_meet_reminders(now)) == 1
    notification = Notification.objects.get()
    assert notification.recipient == mic
    assert "The Hall" in notification.body and "side door" in notification.body
    assert scheduled.queue_meet_reminders(now + datetime.timedelta(minutes=5)) == []


def test_meet_reminder_not_early_or_for_cancelled(event, mic):
    now = timezone.now()
    event.meet_at = now + datetime.timedelta(hours=5)
    event.save()
    clear()
    assert scheduled.queue_meet_reminders(now) == []
    event.meet_at = now + datetime.timedelta(hours=1)
    event.status = Event.CANCELLED
    event.save()
    clear()
    assert scheduled.queue_meet_reminders(now) == []


def test_rescheduled_meet_reminds_again(event, mic):
    now = timezone.now()
    event.meet_at = now + datetime.timedelta(hours=1)
    event.save()
    clear()
    assert len(scheduled.queue_meet_reminders(now)) == 1
    event.meet_at = now + datetime.timedelta(hours=1, minutes=30)
    event.save()
    clear_changes = Notification.objects.filter(kind="rig_changed")
    clear_changes.delete()
    assert len(scheduled.queue_meet_reminders(now)) == 1


def set_up_not_checked_in(event, now, muted=False):
    from notifications.models import NotificationPreference

    if muted:
        NotificationPreference.objects.create(user=event.mic, kind="not_checked_in", push=False, email=False)
    event.meet_at = now - datetime.timedelta(minutes=30)
    event.save()
    clear()


def test_not_checked_in_nudge_can_be_muted(event, mic):
    now = timezone.now()
    set_up_not_checked_in(event, now, muted=True)
    assert scheduled.queue_missing_checkins(now) == []


def test_not_checked_in_nudge(event, mic):
    now = timezone.now()
    set_up_not_checked_in(event, now)
    assert len(scheduled.queue_missing_checkins(now)) == 1
    assert scheduled.queue_missing_checkins(now) == []


def test_not_checked_in_nudge_skips_people_who_checked_in(event, mic):
    now = timezone.now()
    set_up_not_checked_in(event, now)
    EventCheckIn.objects.create(event=event, person=mic, time=now - datetime.timedelta(minutes=5))
    assert scheduled.queue_missing_checkins(now) == []


def test_not_checked_in_nudge_waits_and_gives_up(event, mic):
    now = timezone.now()
    set_up_not_checked_in(event, now)
    assert scheduled.queue_missing_checkins(now - datetime.timedelta(minutes=15)) == []
    assert scheduled.queue_missing_checkins(now + datetime.timedelta(hours=4)) == []


def test_stale_auth_request_nudges_sender(event, mic, other):
    now = timezone.now()
    event.auth_request_by = other
    event.auth_request_at = now - datetime.timedelta(days=4)
    event.auth_request_to = "client@example.com"
    event.save()
    clear()
    assert len(scheduled.queue_stale_auth_requests(now)) == 1
    notification = Notification.objects.get()
    assert notification.recipient == other and notification.kind == "auth_pending"
    assert scheduled.queue_stale_auth_requests(now) == []


def test_recent_or_completed_auth_request_does_not_nudge(event, other):
    now = timezone.now()
    event.auth_request_by = other
    event.auth_request_at = now - datetime.timedelta(days=1)
    event.save()
    clear()
    assert scheduled.queue_stale_auth_requests(now) == []
    event.auth_request_at = now - datetime.timedelta(days=10)
    event.purchase_order = "PO123"
    event.save()
    assert scheduled.queue_stale_auth_requests(now) == []


def finance_user():
    from django.contrib.auth.models import Group

    user = make_user("finny")
    user.groups.add(Group.objects.get_or_create(name="Finance")[0])
    return user


def test_finished_event_notifies_finance_once(mic):
    finny = finance_user()
    event = Event.objects.create(
        name="Done",
        start_date=timezone.localdate() - datetime.timedelta(days=2),
        end_date=timezone.localdate() - datetime.timedelta(days=1),
    )
    clear()
    assert len(scheduled.queue_waiting_invoices()) == 1
    assert Notification.objects.get().recipient == finny
    assert scheduled.queue_waiting_invoices() == []
    assert event.display_id in Notification.objects.get().title


def test_invoiced_old_and_unfinished_events_are_ignored(mic):
    finance_user()
    today = timezone.localdate()
    Event.objects.create(name="Today", start_date=today)
    Event.objects.create(name="Ancient", start_date=today - datetime.timedelta(days=90))
    Event.objects.create(name="Cancelled", start_date=today - datetime.timedelta(days=2), status=Event.CANCELLED)
    invoiced = Event.objects.create(name="Invoiced", start_date=today - datetime.timedelta(days=2))
    Invoice.objects.create(event=invoiced)
    clear()
    assert scheduled.queue_waiting_invoices() == []


def test_only_finance_group_is_notified(mic, other):
    finance_user()
    Event.objects.create(name="Done", start_date=timezone.localdate() - datetime.timedelta(days=2))
    clear()
    scheduled.queue_waiting_invoices()
    assert not Notification.objects.filter(recipient__in=[mic, other]).exists()


def test_send_notifications_command(event, mic, capsys):
    now = timezone.now()
    event.meet_at = now + datetime.timedelta(hours=1)
    event.save()
    clear()
    call_command("send_notifications")
    assert "meet_reminders: 1" in capsys.readouterr().out
    assert Notification.objects.get().delivered_at is not None
    call_command("send_notifications", "--quiet")
    assert capsys.readouterr().out == ""

import datetime

import pytest
from django.utils import timezone
from reversion import revisions as reversion

from notifications.models import Notification
from RIGS.models import Event, Venue

pytestmark = pytest.mark.django_db


def kinds_for(user):
    return list(Notification.objects.filter(recipient=user).values_list("kind", flat=True))


def test_cancelling_notifies_mic(event, mic):
    Notification.objects.all().delete()
    event.status = Event.CANCELLED
    event.save()
    notification = Notification.objects.get(recipient=mic)
    assert notification.kind == "rig_changed"
    assert "was cancelled" in notification.title
    assert notification.url == event.get_absolute_url()


def test_reinstating_a_cancelled_rig_notifies_mic(event, mic):
    event.status = Event.CANCELLED
    event.save()
    Notification.objects.all().delete()
    event.status = Event.PROVISIONAL
    event.save()
    assert "no longer cancelled" in Notification.objects.get(recipient=mic).body


def test_date_change_notifies_mic(event, mic):
    Notification.objects.all().delete()
    event.start_date = event.start_date + datetime.timedelta(days=1)
    event.save()
    assert "date is now" in Notification.objects.get(recipient=mic).body


def test_venue_meet_and_access_changes_are_described(event, mic):
    Notification.objects.all().delete()
    event.venue = Venue.objects.create(name="The Hall")
    event.meet_at = timezone.now() + datetime.timedelta(days=4)
    event.access_at = timezone.now() + datetime.timedelta(days=4, hours=1)
    event.save()
    body = Notification.objects.get(recipient=mic).body
    assert "venue is now The Hall" in body
    assert "meet is now" in body
    assert "access is now" in body


def test_quick_edits_are_merged_into_one_notification(event, mic):
    Notification.objects.all().delete()
    event.start_date = event.start_date + datetime.timedelta(days=1)
    event.save()
    event.venue = Venue.objects.create(name="The Hall")
    event.save()
    notification = Notification.objects.get(recipient=mic)
    assert "date is now" in notification.body and "venue is now" in notification.body


@pytest.mark.parametrize("field,value", [("name", "Renamed"), ("notes", "Bring ladders"), ("description", "Loud")])
def test_irrelevant_edits_do_not_notify(event, mic, field, value):
    Notification.objects.all().delete()
    setattr(event, field, value)
    event.save()
    assert not Notification.objects.exists()


def test_no_notification_without_a_mic(event, mic):
    event.mic = None
    event.save()
    Notification.objects.all().delete()
    event.status = Event.CANCELLED
    event.save()
    assert not Notification.objects.exists()


def test_mic_is_not_told_about_their_own_edit(event, mic):
    Notification.objects.all().delete()
    with reversion.create_revision():
        reversion.set_user(mic)
        event.status = Event.CANCELLED
        event.save()
    assert not Notification.objects.exists()


def test_someone_elses_edit_notifies_mic(event, mic, other):
    Notification.objects.all().delete()
    with reversion.create_revision():
        reversion.set_user(other)
        event.status = Event.CANCELLED
        event.save()
    assert kinds_for(mic) == ["rig_changed"]


def test_assigning_a_mic_on_create(mic):
    Event.objects.create(name="New", start_date=timezone.localdate(), mic=mic)
    assert kinds_for(mic) == ["mic_assigned"]


def test_assigning_a_mic_later_and_removing(event, mic, other):
    Notification.objects.all().delete()
    event.mic = other
    event.save()
    assert kinds_for(other) == ["mic_assigned"]
    assert kinds_for(mic) == ["mic_assigned"]
    assert "no longer MIC" in Notification.objects.get(recipient=mic).title
    assert "You're MIC" in Notification.objects.get(recipient=other).title


def test_self_assignment_is_not_announced(event, mic, other):
    Notification.objects.all().delete()
    with reversion.create_revision():
        reversion.set_user(other)
        event.mic = other
        event.save()
    assert kinds_for(other) == []


def test_new_mic_gets_only_the_assignment_not_a_change(event, mic, other):
    Notification.objects.all().delete()
    event.mic = other
    event.status = Event.CANCELLED
    event.save()
    assert kinds_for(other) == ["mic_assigned"]


def test_a_failure_while_queueing_never_breaks_saving(event, mic, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("nope")

    monkeypatch.setattr("notifications.triggers.notify", boom)
    event.status = Event.CANCELLED
    event.save()
    event.refresh_from_db()
    assert event.status == Event.CANCELLED

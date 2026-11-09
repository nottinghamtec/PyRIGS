import datetime
from smtplib import SMTPException
from types import SimpleNamespace
from unittest import mock

import pytest
from django.contrib.auth.models import Group, Permission
from django.core import mail
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone

from assets.models import PATTestBatch
from badges.awarding import send_badge_emails
from badges.models import BadgeAward, BadgeSettings
from notifications import triggers
from notifications.models import Notification, NotificationPreference
from notifications.tests.conftest import make_user
from RIGS.models import Event, EventAuthorisation, EventCheckIn, RiskAssessment
from training import models as training

pytestmark = pytest.mark.django_db


def mine(user, kind=None):
    notifications = Notification.objects.filter(recipient=user)
    return notifications.filter(kind=kind) if kind else notifications


@pytest.fixture
def reviewer(client):
    user = make_user("reviewer")
    user.user_permissions.add(
        *Permission.objects.filter(codename__in=["review_riskassessment", "view_riskassessment", "view_event"])
    )
    client.force_login(user)
    return user


@pytest.fixture
def assessment(event):
    return RiskAssessment.objects.create(
        event=event,
        nonstandard_equipment=False,
        nonstandard_use=False,
        contractors=False,
        other_companies=False,
        crew_fatigue=False,
        big_power=False,
        generators=False,
        other_companies_power=False,
        nonstandard_equipment_power=False,
        multiple_electrical_environments=False,
        power_mic=event.mic,
        noise_monitoring=False,
        known_venue=True,
        safe_loading=True,
        safe_storage=True,
        area_outside_of_control=True,
        barrier_required=True,
        nonstandard_emergency_procedure=True,
        special_structures=False,
        suspended_structures=False,
        outside=False,
        parking_and_access=False,
    )


def test_marking_reviewed_notifies_mic(client, reviewer, event, mic, assessment):
    Notification.objects.all().delete()
    client.get(reverse("ra_review", kwargs={"pk": assessment.pk}))
    notification = mine(mic).get()
    assert notification.kind == "review_complete"
    assert "reviewed" in notification.title and "Reviewer" in notification.body
    assert notification.url == assessment.get_absolute_url()


def test_mic_reviewing_their_own_is_silent(client, mic, assessment):
    Notification.objects.all().delete()
    mic.user_permissions.add(Permission.objects.get(codename="review_riskassessment"))
    client.force_login(mic)
    client.get(reverse("ra_review", kwargs={"pk": assessment.pk}))
    assert not Notification.objects.exists()


def authorisation(event, sender):
    return EventAuthorisation(event=event, email="client@example.com", name="Client", amount=10, sent_by=sender)


def test_authorisation_notifies_sender_and_mic(event, mic, other):
    triggers.auth_completed(authorisation(event, other), True)
    assert mine(other, "auth_completed").count() == 1
    assert mine(mic, "auth_completed").count() == 1
    assert not Notification.objects.filter(kind="auth_bounced").exists()


def test_authorisation_is_one_notification_when_sender_is_mic(event, mic):
    triggers.auth_completed(authorisation(event, mic), True)
    assert mine(mic, "auth_completed").count() == 1


def test_undelivered_authorisation_confirmation_is_reported(event, mic, other):
    triggers.auth_completed(authorisation(event, other), False)
    assert "confirmation not delivered" in mine(other, "auth_bounced").get().title


def test_authorisation_request_bounce(client, event, mic, other):
    other.email = "teccie@nottinghamtec.co.uk"
    other.is_superuser = True
    other.save()
    client.force_login(other)
    url = reverse("event_authorise_request", kwargs={"pk": event.pk})
    with mock.patch("django.core.mail.EmailMultiAlternatives.send", side_effect=SMTPException("refused")):
        response = client.post(url, {"email": "nobody@nowhere.test"})
    assert response.status_code == 200
    assert any("couldn't be delivered" in str(m) for m in response.context["messages"])
    assert mine(other, "auth_bounced").count() == 1
    event.refresh_from_db()
    assert event.auth_request_at is None


def test_authorisation_request_success_is_unchanged(client, event, other):
    other.email = "teccie@nottinghamtec.co.uk"
    other.is_superuser = True
    other.save()
    client.force_login(other)
    response = client.post(reverse("event_authorise_request", kwargs={"pk": event.pk}), {"email": "client@example.com"})
    assert response.status_code == 302
    event.refresh_from_db()
    assert event.auth_request_by == other and event.auth_request_at is not None
    assert not Notification.objects.filter(kind="auth_bounced").exists()


@pytest.fixture
def levels(db):
    category = training.TrainingCategory.objects.create(reference_number=1, name="Basics")
    items = [
        training.TrainingItem.objects.create(category=category, reference_number=n, name=f"Item {n}") for n in (1, 2)
    ]
    level = training.TrainingLevel.objects.create(level=training.TrainingLevel.TA)
    for item in items:
        training.TrainingLevelRequirement.objects.create(
            level=level, item=item, depth=training.TrainingItemQualification.PASSED_OUT
        )
    return SimpleNamespace(items=items, level=level)


def qualify(trainee, supervisor, item, depth=training.TrainingItemQualification.PASSED_OUT):
    return training.TrainingItemQualification.objects.create(
        trainee=trainee, supervisor=supervisor, item=item, depth=depth, date=timezone.localdate()
    )


@pytest.fixture
def trainee(db):
    return make_user("trainee")


@pytest.fixture
def trainer(db):
    return make_user("trainer", is_supervisor=True)


def test_trainer_logging_notifies_trainee(trainee, trainer, levels):
    qualify(trainee, trainer, levels.items[0], training.TrainingItemQualification.STARTED)
    notification = mine(trainee, "training_logged").get()
    assert "Trainer logged training for you" == notification.title
    assert "Training Started in" in notification.body
    assert not mine(trainer, "training_logged").exists()


def test_session_of_several_items_is_one_notification(trainee, trainer, levels):
    for item in levels.items:
        qualify(trainee, trainer, item, training.TrainingItemQualification.COMPLETE)
    notification = mine(trainee, "training_logged").get()
    assert "Item 1" in notification.body and "Item 2" in notification.body


def test_logging_for_yourself_is_silent(trainer, levels):
    qualify(trainer, trainer, levels.items[0])
    assert not mine(trainer, "training_logged").exists()


def test_reaching_a_levels_requirements(trainee, trainer, levels):
    qualify(trainee, trainer, levels.items[0])
    assert not mine(trainee, "level_ready").exists()
    qualify(trainee, trainer, levels.items[1])
    own = mine(trainee, "level_ready").get()
    assert "You meet the requirements" in own.title
    assert not mine(trainer, "level_ready").exists()


def test_level_ready_only_once_and_not_if_already_confirmed(trainee, trainer, levels):
    qualify(trainee, trainer, levels.items[0])
    qualify(trainee, trainer, levels.items[1])
    training.TrainingItemQualification.objects.filter(trainee=trainee, item=levels.items[1]).first().save()
    assert mine(trainee, "level_ready").count() == 1
    Notification.objects.all().delete()
    other_trainee = make_user("someoneelse")
    qualify(other_trainee, trainer, levels.items[0])
    training.TrainingLevelQualification.objects.create(trainee=other_trainee, level=levels.level)
    qualify(other_trainee, trainer, levels.items[1])
    assert not mine(other_trainee, "level_ready").exists()


def test_pat_testers_are_told_about_a_finished_batch(db):
    group = Group.objects.create(name="PAT Testers")
    uploader, tester, bystander = make_user("uploader"), make_user("tester"), make_user("bystander")
    uploader.groups.add(group)
    tester.groups.add(group)
    batch = PATTestBatch.objects.create(
        original_filename="results.sss", file="x", sha256="0" * 64, uploaded_by=uploader
    )
    summary = SimpleNamespace(imported=[1, 2, 3], replaced=[4])
    triggers.pat_batch_complete(batch, summary, uploader)
    notification = mine(tester, "pat_batch_complete").get()
    assert "4 results imported" in notification.body
    assert notification.url == batch.get_absolute_url()
    assert not mine(uploader).exists() and not mine(bystander).exists()


def test_checkout_nag_pushes_and_respects_email_preference(event, mic):
    now = timezone.now()
    EventCheckIn.objects.create(event=event, person=mic, time=now - datetime.timedelta(hours=40))
    call_command("send_checkout_nags")
    assert len(mail.outbox) == 1
    assert "/checkin/" in mine(mic, "checkout_nag").get().url
    mail.outbox.clear()
    Notification.objects.all().delete()
    NotificationPreference.objects.create(user=mic, kind="checkout_nag", push=True, email=False)
    call_command("send_checkout_nags")
    assert mail.outbox == []
    assert mine(mic, "checkout_nag").count() == 1


def test_ra_reminder_pushes_and_respects_email_preference(mic):
    soon = Event.objects.create(name="Soon", start_date=timezone.localdate() + datetime.timedelta(days=1), mic=mic)
    Notification.objects.all().delete()
    call_command("send_reminders")
    assert len(mail.outbox) == 1
    assert mine(mic, "ra_reminder").get().title.startswith(soon.display_id)
    mail.outbox.clear()
    NotificationPreference.objects.create(user=mic, kind="ra_reminder", push=True, email=False)
    call_command("send_reminders")
    assert mail.outbox == []
    assert mine(mic, "ra_reminder").count() == 1


def test_badges_push_even_when_email_is_off(mic):
    BadgeSettings.objects.update_or_create(pk=1, defaults={"badges_live": True})
    NotificationPreference.objects.create(user=mic, kind="badge_earned", push=True, email=False)
    BadgeAward.objects.create(profile=mic, slug="headliner", awarded_at=timezone.now(), email=BadgeAward.EMAIL_PENDING)
    send_badge_emails()
    assert mine(mic, "badge_earned").count() == 1
    assert mail.outbox == []
    send_badge_emails()
    assert mine(mic, "badge_earned").count() == 1


def test_admins_are_pushed_when_users_register(settings, db):
    settings.ADMINS = [("IT", "boss@example.com")]
    boss = make_user("boss")
    boss.email = "boss@example.com"
    boss.save()
    newcomer = make_user(
        "newcomer",
    )
    from RIGS import signals

    with mock.patch("RIGS.models.Profile.users_awaiting_approval_count", return_value=1):
        signals.send_admin_awaiting_approval_email(newcomer, mock.Mock())
    assert mine(boss, "admin_approval").count() == 1
    assert len(mail.outbox) == 1

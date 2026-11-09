import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

pytestmark = pytest.mark.django_db(transaction=True)

BEFORE = [("RIGS", "0064_search_vocabulary"), ("notifications", "0001_initial")]
AFTER = [("RIGS", "0065_remove_profile_badge_emails"), ("notifications", "0002_move_badge_email_preferences")]


def migrate(targets):
    executor = MigrationExecutor(connection)
    executor.migrate(targets)
    return executor.loader.project_state(targets).apps


def test_badge_email_opt_outs_become_preferences():
    old = migrate(BEFORE)
    Profile = old.get_model("RIGS", "Profile")
    opted_out = Profile.objects.create(username="out", badge_emails=False)
    Profile.objects.create(username="in", badge_emails=True)

    new = migrate(AFTER)
    NotificationPreference = new.get_model("notifications", "NotificationPreference")
    preference = NotificationPreference.objects.get()
    assert (preference.user_id, preference.kind, preference.push, preference.email) == (
        opted_out.pk,
        "badge_earned",
        True,
        False,
    )

    old = migrate(BEFORE)
    Profile = old.get_model("RIGS", "Profile")
    assert list(Profile.objects.filter(badge_emails=False).values_list("username", flat=True)) == ["out"]
    migrate(AFTER)

from django.db import migrations

KIND = "badge_earned"


def move_to_preferences(apps, schema_editor):
    Profile = apps.get_model("RIGS", "Profile")
    NotificationPreference = apps.get_model("notifications", "NotificationPreference")
    NotificationPreference.objects.bulk_create(
        [
            NotificationPreference(user_id=pk, kind=KIND, push=True, email=False)
            for pk in Profile.objects.filter(badge_emails=False).values_list("pk", flat=True)
        ],
        ignore_conflicts=True,
    )


def move_to_profiles(apps, schema_editor):
    Profile = apps.get_model("RIGS", "Profile")
    NotificationPreference = apps.get_model("notifications", "NotificationPreference")
    opted_out = NotificationPreference.objects.filter(kind=KIND, email=False).values_list("user_id", flat=True)
    Profile.objects.filter(pk__in=list(opted_out)).update(badge_emails=False)


class Migration(migrations.Migration):
    dependencies = [
        ("notifications", "0001_initial"),
        ("RIGS", "0064_search_vocabulary"),
    ]

    operations = [migrations.RunPython(move_to_preferences, move_to_profiles)]

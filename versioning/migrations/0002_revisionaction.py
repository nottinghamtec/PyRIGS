from django.db import migrations, models
import django.db.models.deletion

CONVERTED_PREFIX = "Converted enquiry "
DELETED_PREFIX = "Deleted enquiry "


def backfill_actions(apps, schema_editor):
    Revision = apps.get_model("reversion", "Revision")
    RevisionAction = apps.get_model("versioning", "RevisionAction")
    actions = []
    for pk, comment in Revision.objects.filter(comment__startswith=CONVERTED_PREFIX).values_list("pk", "comment"):
        actions.append(RevisionAction(revision_id=pk, kind="converted", name=comment[len(CONVERTED_PREFIX) :]))
    for pk, comment in Revision.objects.filter(comment__startswith=DELETED_PREFIX).values_list("pk", "comment"):
        actions.append(RevisionAction(revision_id=pk, kind="deleted", name=f"enquiry {comment[len(DELETED_PREFIX) :]}"))
    RevisionAction.objects.bulk_create(actions)


class Migration(migrations.Migration):

    dependencies = [
        ("reversion", "0002_add_index_on_version_for_content_type_and_db"),
        ("versioning", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="RevisionAction",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "kind",
                    models.CharField(choices=[("converted", "Converted"), ("deleted", "Deleted")], max_length=16),
                ),
                ("name", models.TextField()),
                (
                    "revision",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE, related_name="action", to="reversion.revision"
                    ),
                ),
            ],
        ),
        migrations.RunPython(backfill_actions, migrations.RunPython.noop),
    ]

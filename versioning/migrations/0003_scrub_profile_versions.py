import json

from django.db import migrations

SECRET_FIELDS = ("password", "api_key", "last_login")
BATCH_SIZE = 500


def scrub_profile_versions(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Version = apps.get_model("reversion", "Version")
    content_type = ContentType.objects.filter(app_label="RIGS", model="profile").first()
    if content_type is None:
        return
    batch = []
    for version in Version.objects.filter(content_type=content_type, format="json").iterator(chunk_size=BATCH_SIZE):
        data = json.loads(version.serialized_data)
        for entry in data:
            for field in SECRET_FIELDS:
                entry["fields"].pop(field, None)
        version.serialized_data = json.dumps(data)
        batch.append(version)
        if len(batch) >= BATCH_SIZE:
            Version.objects.bulk_update(batch, ["serialized_data"])
            batch = []
    Version.objects.bulk_update(batch, ["serialized_data"])


class Migration(migrations.Migration):

    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        ("reversion", "0002_add_index_on_version_for_content_type_and_db"),
        ("versioning", "0002_revisionaction"),
    ]

    operations = [
        migrations.RunPython(scrub_profile_versions, migrations.RunPython.noop),
    ]

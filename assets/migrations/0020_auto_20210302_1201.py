# Generated by Django 3.1.7 on 2021-03-02 12:01

from django.db import migrations


def postgres_migration_prep(apps, schema_editor):
    model = apps.get_model("assets", "Supplier")
    fields = ["address", "email", "notes", "phone"]
    for field in fields:
        filter_param = {"{}__isnull".format(field): True}
        update_param = {field: ""}
        model.objects.filter(**filter_param).update(**update_param)


class Migration(migrations.Migration):

    dependencies = [
        ('assets', '0019_fix_cabletype'),
    ]

    operations = [
        migrations.RunPython(postgres_migration_prep, migrations.RunPython.noop)
    ]

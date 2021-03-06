# Generated by Django 3.1.5 on 2021-02-08 16:02

from django.db import migrations


def add_default(apps, schema_editor):
    CableType = apps.get_model('assets', 'CableType')
    Connector = apps.get_model('assets', 'Connector')
    for cable_type in CableType.objects.all():
        if cable_type.plug is None:
            cable_type.plug = Connector.objects.first()
        if cable_type.socket is None:
            cable_type.socket = Connector.objects.first()
        cable_type.save()


class Migration(migrations.Migration):

    dependencies = [
        ('assets', '0018_auto_20200415_1940'),
    ]

    operations = [
        migrations.RunPython(add_default, migrations.RunPython.noop)
    ]

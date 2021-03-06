# Generated by Django 2.0.13 on 2020-02-18 16:27

from django.db import migrations
from django.db.models import Q


def move_cable_type_data(apps, schema_editor):
    Asset = apps.get_model('assets', 'Asset')
    CableType = apps.get_model('assets', 'CableType')
    for asset in Asset.objects.filter(is_cable=True):
        # Only create one type per...well...type
        if(not CableType.objects.filter(Q(plug=asset.plug) & Q(socket=asset.socket))):
            cabletype = CableType.objects.create(plug=asset.plug, socket=asset.socket, circuits=asset.circuits, cores=asset.cores)
            asset.save()
            cabletype.save()


class Migration(migrations.Migration):

    dependencies = [
        ('assets', '0011_auto_20200218_1617'),
    ]

    operations = [
        migrations.RunPython(move_cable_type_data)
    ]

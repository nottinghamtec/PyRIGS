# Generated by Django 3.2.11 on 2022-01-12 19:11

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('assets', '0021_auto_20210302_1204'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='cabletype',
            unique_together={('plug', 'socket', 'circuits', 'cores')},
        ),
    ]

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import django.db.models.deletion
from django.db import models, migrations


class Migration(migrations.Migration):
    dependencies = [
        ('RIGS', '0023_auto_20150529_0048'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='based_on',
            field=models.ForeignKey(related_name='future_events', on_delete=django.db.models.deletion.SET_NULL,
                                    blank=True, to='RIGS.Event', null=True),
        ),
    ]

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):
    dependencies = [
        ('RIGS', '0011_venue_address'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='eventitem',
            options={'ordering': ['order']},
        ),
        migrations.AlterModelOptions(
            name='vatrate',
            options={'ordering': ['-start_at'], 'get_latest_by': 'start_at'},
        ),
    ]

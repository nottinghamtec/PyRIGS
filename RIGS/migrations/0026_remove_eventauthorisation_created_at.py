# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('RIGS', '0025_eventauthorisation'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='eventauthorisation',
            name='created_at',
        ),
    ]

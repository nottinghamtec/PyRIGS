# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('DiscourseAuth', '0002_auto_20170126_1513'),
    ]

    operations = [
        migrations.RenameField(
            model_name='authattempt',
            old_name='created_at',
            new_name='created',
        ),
    ]

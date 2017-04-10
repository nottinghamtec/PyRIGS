# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('DiscourseAuth', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='authattempt',
            old_name='created',
            new_name='created_at',
        ),
    ]

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('DiscourseAuth', '0004_discourseuserlink'),
    ]

    operations = [
        migrations.AlterField(
            model_name='discourseuserlink',
            name='discourse_user_id',
            field=models.IntegerField(unique=True),
        ),
    ]

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('RIGS', '0024_auto_20160229_2042'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='avatar_template',
            field=models.CharField(max_length=255, null=True, editable=False, blank=True),
        ),
    ]

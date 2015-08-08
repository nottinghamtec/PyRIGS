# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('rigForms', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='schema',
            name='layout',
            field=models.TextField(default=b'[]'),
        ),
    ]

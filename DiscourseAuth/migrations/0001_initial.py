# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import DiscourseAuth.models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='AuthAttempt',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('nonce', models.CharField(default=DiscourseAuth.models.gen_nonce, max_length=25)),
                ('created', models.DateTimeField(auto_now=True)),
            ],
        ),
    ]

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('training', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='trainingrecord',
            name='assessed_trainer',
            field=models.ForeignKey(related_name='trainingrecords_assessed', blank=True, to=settings.AUTH_USER_MODEL, null=True),
        ),
        migrations.AlterField(
            model_name='trainingrecord',
            name='completed_trainer',
            field=models.ForeignKey(related_name='trainingrecords_completed', blank=True, to=settings.AUTH_USER_MODEL, null=True),
        ),
        migrations.AlterField(
            model_name='trainingrecord',
            name='started_trainer',
            field=models.ForeignKey(related_name='trainingrecords_started', blank=True, to=settings.AUTH_USER_MODEL, null=True),
        ),
    ]

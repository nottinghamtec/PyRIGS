# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='TrainingCategory',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('category_number', models.PositiveSmallIntegerField()),
                ('category_name', models.CharField(max_length=50)),
            ],
        ),
        migrations.CreateModel(
            name='TrainingItem',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('item_number', models.PositiveSmallIntegerField()),
                ('item_name', models.CharField(max_length=100)),
                ('category', models.ForeignKey(to='training.TrainingCategory')),
            ],
        ),
        migrations.CreateModel(
            name='TrainingLevelRecord',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('technical_assistant', models.DateField(null=True, blank=True)),
                ('sound_technician', models.DateField(null=True, blank=True)),
                ('sound_supervisor', models.DateField(null=True, blank=True)),
                ('lighting_technician', models.DateField(null=True, blank=True)),
                ('lighting_supervisor', models.DateField(null=True, blank=True)),
                ('power_technician', models.DateField(null=True, blank=True)),
                ('power_supervisor', models.DateField(null=True, blank=True)),
                ('haulage_supervisor', models.DateField(null=True, blank=True)),
                ('trainee', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='TrainingRecord',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('started_date', models.DateField(null=True, blank=True)),
                ('started_notes', models.TextField(null=True, blank=True)),
                ('completed_date', models.DateField(null=True, blank=True)),
                ('completed_notes', models.TextField(null=True, blank=True)),
                ('assessed_date', models.DateField(null=True, blank=True)),
                ('assessed_notes', models.TextField(null=True, blank=True)),
                ('assessed_trainer', models.ForeignKey(related_name='trainingrecords_assessed', to=settings.AUTH_USER_MODEL)),
                ('completed_trainer', models.ForeignKey(related_name='trainingrecords_completed', to=settings.AUTH_USER_MODEL)),
                ('started_trainer', models.ForeignKey(related_name='trainingrecords_started', to=settings.AUTH_USER_MODEL)),
                ('trainee', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
                ('training_item', models.ForeignKey(to='training.TrainingItem')),
            ],
        ),
        migrations.AddField(
            model_name='trainingitem',
            name='training_records',
            field=models.ManyToManyField(to=settings.AUTH_USER_MODEL, through='training.TrainingRecord'),
        ),
        migrations.AlterUniqueTogether(
            name='trainingrecord',
            unique_together=set([('trainee', 'training_item')]),
        ),
    ]

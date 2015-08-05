# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import RIGS.models


class Migration(migrations.Migration):

    dependencies = [
        ('RIGS', '0023_auto_20150529_0048'),
    ]

    operations = [
        migrations.CreateModel(
            name='Form',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('data', models.TextField(default=b'{}')),
                ('event', models.ForeignKey(related_name='forms', to='RIGS.Event')),
            ],
            bases=(models.Model, RIGS.models.RevisionMixin),
        ),
        migrations.CreateModel(
            name='Schema',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('start_at', models.DateTimeField()),
                ('schema', models.TextField(default=b'{}')),
                ('layout', models.TextField(default=b'{}')),
                ('comment', models.CharField(max_length=255)),
            ],
            options={
                'ordering': ['-start_at'],
                'get_latest_by': 'start_at',
            },
            bases=(models.Model, RIGS.models.RevisionMixin),
        ),
        migrations.CreateModel(
            name='Type',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255)),
                ('description', models.CharField(max_length=255, null=True, blank=True)),
                ('active', models.BooleanField(default=True)),
            ],
            bases=(models.Model, RIGS.models.RevisionMixin),
        ),
        migrations.AddField(
            model_name='schema',
            name='schema_type',
            field=models.ForeignKey(related_name='schemas', to='rigForms.Type'),
        ),
        migrations.AddField(
            model_name='form',
            name='schema',
            field=models.ForeignKey(related_name='forms', to='rigForms.Schema'),
        ),
    ]

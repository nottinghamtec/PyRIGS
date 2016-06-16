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
            name='Hire',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField(null=True, blank=True)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('start_transport', models.IntegerField(blank=True, null=True, choices=[(0, b'TEC Transport'), (1, b'Provider Transports')])),
                ('mic', models.ForeignKey(related_name='hire_mic', verbose_name=b'MIC', blank=True, to=settings.AUTH_USER_MODEL, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Provider',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=50)),
                ('phone', models.CharField(max_length=15, null=True, blank=True)),
                ('email', models.EmailField(max_length=254, null=True, blank=True)),
                ('address', models.TextField(null=True, blank=True)),
                ('notes', models.TextField(null=True, blank=True)),
            ],
        ),
        migrations.AddField(
            model_name='hire',
            name='provider',
            field=models.ForeignKey(blank=True, to='subhire.Provider', null=True),
        ),
    ]

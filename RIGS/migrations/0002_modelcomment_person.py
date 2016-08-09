# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import models, migrations


class Migration(migrations.Migration):
    dependencies = [
        ('RIGS', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ModelComment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('postedAt', models.DateTimeField(auto_now=True)),
                ('message', models.TextField()),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Person',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=50)),
                ('phone', models.CharField(max_length=15, null=True, blank=True)),
                ('email', models.EmailField(max_length=75, null=True, blank=True)),
                ('address', models.TextField(null=True, blank=True)),
                ('comments', models.ManyToManyField(to='RIGS.ModelComment')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]

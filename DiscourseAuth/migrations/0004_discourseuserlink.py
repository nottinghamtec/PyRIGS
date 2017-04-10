# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('DiscourseAuth', '0003_auto_20170126_1621'),
    ]

    operations = [
        migrations.CreateModel(
            name='DiscourseUserLink',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('discourse_user_id', models.IntegerField()),
                ('django_user', models.OneToOneField(to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]

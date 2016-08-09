# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import django.contrib.auth.models
import django.core.validators
from django.db import models, migrations


class Migration(migrations.Migration):
    dependencies = [
        ('RIGS', '0022_auto_20150424_2104'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='profile',
            options={'permissions': (('view_profile', 'Can view Profile'),)},
        ),
        migrations.AlterModelManagers(
            name='profile',
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.AlterField(
            model_name='event',
            name='collector',
            field=models.CharField(max_length=255, null=True, verbose_name=b'collected by', blank=True),
        ),
        migrations.AlterField(
            model_name='organisation',
            name='email',
            field=models.EmailField(max_length=254, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='person',
            name='email',
            field=models.EmailField(max_length=254, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='profile',
            name='email',
            field=models.EmailField(max_length=254, verbose_name='email address', blank=True),
        ),
        migrations.AlterField(
            model_name='profile',
            name='groups',
            field=models.ManyToManyField(related_query_name='user', related_name='user_set', to='auth.Group',
                                         blank=True,
                                         help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.',
                                         verbose_name='groups'),
        ),
        migrations.AlterField(
            model_name='profile',
            name='last_login',
            field=models.DateTimeField(null=True, verbose_name='last login', blank=True),
        ),
        migrations.AlterField(
            model_name='profile',
            name='username',
            field=models.CharField(error_messages={'unique': 'A user with that username already exists.'},
                                   max_length=30, validators=[django.core.validators.RegexValidator('^[\\w.@+-]+$',
                                                                                                    'Enter a valid username. This value may contain only letters, numbers and @/./+/-/_ characters.',
                                                                                                    'invalid')],
                                   help_text='Required. 30 characters or fewer. Letters, digits and @/./+/-/_ only.',
                                   unique=True, verbose_name='username'),
        ),
        migrations.AlterField(
            model_name='venue',
            name='email',
            field=models.EmailField(max_length=254, null=True, blank=True),
        ),
    ]

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import models, migrations


class Migration(migrations.Migration):
    dependencies = [
        ('RIGS', '0015_auto_20141208_0233'),
    ]

    operations = [
        migrations.CreateModel(
            name='Invoice',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('invoice_date', models.DateField(auto_now_add=True)),
                ('void', models.BooleanField()),
                ('event', models.OneToOneField(to='RIGS.Event')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date', models.DateField()),
                ('amount', models.DecimalField(help_text=b'Please use ex. VAT', max_digits=10, decimal_places=2)),
                ('method', models.CharField(max_length=2,
                                            choices=[(b'C', b'Cash'), (b'I', b'Internal'), (b'E', b'External'),
                                                     (b'SU', b'SU Core'), (b'M', b'Members')])),
                ('invoice', models.ForeignKey(to='RIGS.Invoice')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterField(
            model_name='event',
            name='mic',
            field=models.ForeignKey(related_name='event_mic', verbose_name=b'MIC', blank=True,
                                    to=settings.AUTH_USER_MODEL, null=True),
            preserve_default=True,
        ),
    ]

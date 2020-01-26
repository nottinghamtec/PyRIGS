# -*- coding: utf-8 -*-


from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):
    dependencies = [
        ('RIGS', '0008_auto_20141105_1908'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='based_on',
            field=models.ForeignKey(to='RIGS.Event', related_name='future_events', blank=True, null=True, on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='event',
            name='checked_in_by',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL, related_name='event_checked_in', blank=True,
                                    null=True, on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='event',
            name='mic',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL, related_name='event_mic', blank=True, null=True, on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='event',
            name='organisation',
            field=models.ForeignKey(to='RIGS.Organisation', blank=True, null=True, on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='event',
            name='status',
            field=models.IntegerField(default=0,
                                      choices=[(0, 'Provisional'), (1, 'Confirmed'), (2, 'Booked'), (3, 'Cancelled')]),
            preserve_default=True,
        ),
    ]

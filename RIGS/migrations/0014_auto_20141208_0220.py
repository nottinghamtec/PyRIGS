# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('RIGS', '0013_auto_20141202_0041'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='venue',
            field=models.ForeignKey(blank=True, to='RIGS.Venue', null=True, on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='eventitem',
            name='event',
            field=models.ForeignKey(related_name='items', blank=True, to='RIGS.Event', on_delete=models.CASCADE),
            preserve_default=True,
        ),
    ]

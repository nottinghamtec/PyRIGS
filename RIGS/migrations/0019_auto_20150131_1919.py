# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('RIGS', '0018_auto_20150130_0016'),
    ]

    operations = [
        migrations.AlterField(
            model_name='payment',
            name='method',
            field=models.CharField(blank=True, max_length=2, null=True, choices=[(b'C', b'Cash'), (b'I', b'Internal'), (b'E', b'External'), (b'SU', b'SU Core')]),
            preserve_default=True,
        ),
    ]

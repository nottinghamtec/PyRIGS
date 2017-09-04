# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):
    dependencies = [
        ('RIGS', '0017_auto_20150129_2041'),
    ]

    operations = [
        migrations.AlterField(
            model_name='invoice',
            name='void',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='payment',
            name='method',
            field=models.CharField(max_length=2, choices=[(b'C', b'Cash'), (b'I', b'Internal'), (b'E', b'External'),
                                                          (b'SU', b'SU Core')]),
            preserve_default=True,
        ),
    ]

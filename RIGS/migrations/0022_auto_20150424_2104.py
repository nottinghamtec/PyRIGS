# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('RIGS', '0021_auto_20150420_1155'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='collector',
            field=models.CharField(max_length=255, null=True, verbose_name=b'Collected by', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='event',
            name='purchase_order',
            field=models.CharField(max_length=255, null=True, verbose_name=b'PO', blank=True),
            preserve_default=True,
        ),
    ]

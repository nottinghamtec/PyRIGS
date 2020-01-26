# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('RIGS', '0020_auto_20150303_0243'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='invoice',
            options={'ordering': ['-invoice_date'], 'permissions': (('view_invoice', 'Can view Invoices'),)},
        ),
        migrations.AddField(
            model_name='profile',
            name='api_key',
            field=models.CharField(max_length=40, null=True, editable=False, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='event',
            name='collector',
            field=models.CharField(max_length=255, null=True, verbose_name=b'Collected By', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='profile',
            name='initials',
            field=models.CharField(max_length=5, unique=True, null=True),
            preserve_default=True,
        ),
    ]

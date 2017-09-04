# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):
    dependencies = [
        ('RIGS', '0016_auto_20150127_1905'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='invoice',
            options={'permissions': (('view_invoice', 'Can view Invoices'),)},
        ),
    ]

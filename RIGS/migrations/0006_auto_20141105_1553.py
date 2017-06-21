# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):
    dependencies = [
        ('RIGS', '0005_auto_20141104_1619'),
    ]

    operations = [
        migrations.RenameField(
            model_name='organisation',
            old_name='unionAccount',
            new_name='union_account',
        ),
    ]

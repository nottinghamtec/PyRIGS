# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('RIGS', '0004_organisation'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='initials',
            field=models.CharField(blank=True, max_length=5, unique=True, null=True),
            preserve_default=True,
        ),
    ]

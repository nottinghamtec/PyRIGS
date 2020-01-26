# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):
    dependencies = [
        ('RIGS', '0010_auto_20141105_2219'),
    ]

    operations = [
        migrations.AddField(
            model_name='venue',
            name='address',
            field=models.TextField(blank=True, null=True),
            preserve_default=True,
        ),
    ]

# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('RIGS', '0012_auto_20141106_0253'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='person',
            field=models.ForeignKey(blank=True, null=True, to='RIGS.Person', on_delete=models.CASCADE),
            preserve_default=True,
        ),
    ]

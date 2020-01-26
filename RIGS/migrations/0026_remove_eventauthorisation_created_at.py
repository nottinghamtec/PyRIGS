# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('RIGS', '0025_eventauthorisation'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='eventauthorisation',
            name='created_at',
        ),
    ]

# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('RIGS', '0026_remove_eventauthorisation_created_at'),
    ]

    operations = [
        migrations.AlterField(
            model_name='eventauthorisation',
            name='event',
            field=models.OneToOneField(related_name='authorisation', to='RIGS.Event', on_delete=models.CASCADE),
        ),
    ]

# -*- coding: utf-8 -*-


from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('RIGS', '0027_eventauthorisation_event_singular'),
    ]

    operations = [
        migrations.AddField(
            model_name='eventauthorisation',
            name='sent_by',
            field=models.ForeignKey(default=1, to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE),
            preserve_default=False,
        ),
    ]

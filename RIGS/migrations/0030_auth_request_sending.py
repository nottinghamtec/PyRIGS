# -*- coding: utf-8 -*-


from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('RIGS', '0029_eventauthorisation_sent_by'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='auth_request_at',
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='event',
            name='auth_request_by',
            field=models.ForeignKey(blank=True, to=settings.AUTH_USER_MODEL, null=True, on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='event',
            name='auth_request_to',
            field=models.EmailField(max_length=254, null=True, blank=True),
        ),
    ]

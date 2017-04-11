# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('RIGS', '0028_migrate_purchase_order'),
    ]

    operations = [
        migrations.AddField(
            model_name='eventauthorisation',
            name='sent_by',
            field=models.ForeignKey(default=1, to=settings.AUTH_USER_MODEL),
            preserve_default=False,
        ),
    ]

# Generated by Django 3.2.19 on 2023-06-27 11:25

import RIGS.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('RIGS', '0049_auto_20230529_1123'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='forum_url',
            field=models.URLField(blank=True, null=True, validators=[RIGS.models.validate_forum_url]),
        ),
    ]

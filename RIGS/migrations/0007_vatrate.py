# -*- coding: utf-8 -*-


from django.db import models, migrations
import RIGS.models
import versioning


class Migration(migrations.Migration):
    dependencies = [
        ('RIGS', '0006_auto_20141105_1553'),
    ]

    operations = [
        migrations.CreateModel(
            name='VatRate',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True, serialize=False)),
                ('start_at', models.DateTimeField()),
                ('rate', models.DecimalField(max_digits=6, decimal_places=6)),
                ('comment', models.CharField(max_length=255)),
            ],
            options={
            },
            bases=(models.Model, versioning.versioning.RevisionMixin),
        ),
    ]

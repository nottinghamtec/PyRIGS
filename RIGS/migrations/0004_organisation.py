# -*- coding: utf-8 -*-


from django.db import models, migrations
import RIGS.models
import versioning


class Migration(migrations.Migration):

    dependencies = [
        ('RIGS', '0003_auto_20141031_0219'),
    ]

    operations = [
        migrations.CreateModel(
            name='Organisation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=50)),
                ('phone', models.CharField(null=True, blank=True, max_length=15)),
                ('email', models.EmailField(null=True, blank=True, max_length=75)),
                ('address', models.TextField(null=True, blank=True)),
                ('notes', models.TextField(null=True, blank=True)),
                ('unionAccount', models.BooleanField(default=False)),
            ],
            options={
            },
            bases=(models.Model, versioning.versioning.RevisionMixin),
        ),
    ]

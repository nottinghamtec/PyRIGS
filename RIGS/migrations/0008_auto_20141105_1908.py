# -*- coding: utf-8 -*-


from django.db import models, migrations
from django.conf import settings
import RIGS.models
import versioning


class Migration(migrations.Migration):
    dependencies = [
        ('RIGS', '0007_vatrate'),
    ]

    operations = [
        migrations.CreateModel(
            name='Event',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True, null=True)),
                ('notes', models.TextField(blank=True, null=True)),
                ('status',
                 models.IntegerField(choices=[(0, 'Provisional'), (1, 'Confirmed'), (2, 'Booked'), (3, 'Cancelled')])),
                ('dry_hire', models.BooleanField(default=False)),
                ('is_rig', models.BooleanField(default=True)),
                ('start_date', models.DateField()),
                ('start_time', models.TimeField(blank=True, null=True)),
                ('end_date', models.DateField(blank=True, null=True)),
                ('end_time', models.TimeField(blank=True, null=True)),
                ('access_at', models.DateTimeField(blank=True, null=True)),
                ('meet_at', models.DateTimeField(blank=True, null=True)),
                ('meet_info', models.CharField(blank=True, null=True, max_length=255)),
                ('payment_method', models.CharField(blank=True, null=True, max_length=255)),
                ('payment_received', models.CharField(blank=True, null=True, max_length=255)),
                ('purchase_order', models.CharField(blank=True, null=True, max_length=255)),
                ('based_on', models.ForeignKey(to='RIGS.Event', related_name='future_events', on_delete=models.CASCADE)),
                ('checked_in_by', models.ForeignKey(to=settings.AUTH_USER_MODEL, related_name='event_checked_in', on_delete=models.CASCADE)),
                ('mic', models.ForeignKey(to=settings.AUTH_USER_MODEL, related_name='event_mic', on_delete=models.CASCADE)),
                ('organisation', models.ForeignKey(to='RIGS.Organisation', on_delete=models.CASCADE)),
                ('person', models.ForeignKey(to='RIGS.Person', on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=(models.Model, versioning.versioning.RevisionMixin),
        ),
        migrations.CreateModel(
            name='EventItem',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True, null=True)),
                ('quantity', models.IntegerField()),
                ('cost', models.DecimalField(max_digits=10, decimal_places=2)),
                ('order', models.IntegerField()),
                ('event', models.ForeignKey(to='RIGS.Event', related_name='item', on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Venue',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('phone', models.CharField(blank=True, null=True, max_length=15)),
                ('email', models.EmailField(blank=True, null=True, max_length=75)),
                ('three_phase_available', models.BooleanField(default=False)),
                ('notes', models.TextField(blank=True, null=True)),
            ],
            options={
            },
            bases=(models.Model, versioning.versioning.RevisionMixin),
        ),
        migrations.AddField(
            model_name='event',
            name='venue',
            field=models.ForeignKey(to='RIGS.Venue', on_delete=models.CASCADE),
            preserve_default=True,
        ),
    ]

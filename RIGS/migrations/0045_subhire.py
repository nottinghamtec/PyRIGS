# Generated by Django 3.2.12 on 2022-10-15 19:36

from django.db import migrations, models
import django.db.models.deletion
import versioning.versioning


class Migration(migrations.Migration):

    dependencies = [
        ('RIGS', '0044_profile_is_supervisor'),
    ]

    operations = [
        migrations.CreateModel(
            name='Subhire',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True, default='')),
                ('status', models.IntegerField(choices=[(0, 'Provisional'), (1, 'Confirmed'), (2, 'Booked'), (3, 'Cancelled')], default=0)),
                ('start_date', models.DateField()),
                ('start_time', models.TimeField(blank=True, null=True)),
                ('end_date', models.DateField(blank=True, null=True)),
                ('end_time', models.TimeField(blank=True, null=True)),
                ('purchase_order', models.CharField(blank=True, default='', max_length=255, verbose_name='PO')),
                ('insurance_value', models.DecimalField(decimal_places=2, max_digits=10)),
                ('organisation', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='RIGS.organisation')),
                ('person', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='RIGS.person')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model, versioning.versioning.RevisionMixin),
        ),
    ]
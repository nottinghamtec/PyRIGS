# Generated by Django 2.0.13 on 2019-11-24 13:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('RIGS', '0034_event_risk_assessment_edit_url'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='risk_assessment_edit_url',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='risk assessment'),
        ),
    ]

# Generated by Django 2.0.2 on 2018-03-01 17:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assets', '0002_auto_20180301_1654'),
    ]

    operations = [
        migrations.AlterField(
            model_name='asset',
            name='purchase_price',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
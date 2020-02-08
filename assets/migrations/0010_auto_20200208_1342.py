# Generated by Django 3.0.3 on 2020-02-08 13:42

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('assets', '0009_auto_20200103_2215'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='asset',
            options={'ordering': ['asset_id_prefix', 'asset_id_number'], 'permissions': [('asset_finance', 'Can see financial data for assets')]},
        ),
        migrations.AlterModelOptions(
            name='supplier',
            options={},
        ),
    ]

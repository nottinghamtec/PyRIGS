# Generated by Django 3.0.3 on 2020-02-08 13:42

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('RIGS', '0035_auto_20191124_1319'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='event',
            options={},
        ),
        migrations.AlterModelOptions(
            name='invoice',
            options={'ordering': ['-invoice_date']},
        ),
        migrations.AlterModelOptions(
            name='organisation',
            options={},
        ),
        migrations.AlterModelOptions(
            name='person',
            options={},
        ),
        migrations.AlterModelOptions(
            name='profile',
            options={'verbose_name': 'user', 'verbose_name_plural': 'users'},
        ),
        migrations.AlterModelOptions(
            name='venue',
            options={},
        ),
    ]

# Generated by Django 2.0.13 on 2020-01-10 14:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('RIGS', '0035_auto_20191124_1319'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='is_approved',
            # Approve existing profiles automatically, new ones default false. 
            field=models.BooleanField(default=True),
        ),
    ]

# Generated by Django 3.1 on 2020-08-29 21:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('RIGS', '0047_auto_20200829_2105'),
    ]

    operations = [
        migrations.AlterField(
            model_name='eventchecklistcrew',
            name='end',
            field=models.DateTimeField(default=None),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='eventchecklistcrew',
            name='role',
            field=models.CharField(default=None, max_length=255),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='eventchecklistcrew',
            name='start',
            field=models.DateTimeField(default=None),
            preserve_default=False,
        ),
    ]

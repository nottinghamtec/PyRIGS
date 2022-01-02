# Generated by Django 3.1.13 on 2022-01-02 20:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('training', '0011_auto_20220102_1106'),
    ]

    operations = [
        migrations.AlterField(
            model_name='traininglevel',
            name='department',
            field=models.IntegerField(blank=True, choices=[(0, 'Sound'), (1, 'Lighting'), (2, 'Power'), (3, 'Rigging'), (4, 'Haulage')], null=True),
        ),
        migrations.AlterField(
            model_name='traininglevel',
            name='description',
            field=models.TextField(blank=True),
        ),
    ]

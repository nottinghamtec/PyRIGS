# Generated by Django 3.1.5 on 2021-06-30 15:24

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('training', '0002_auto_20210630_1514'),
    ]

    operations = [
        migrations.AlterField(
            model_name='trainingitem',
            name='category',
            field=models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, related_name='items', to='training.trainingcategory'),
        ),
    ]

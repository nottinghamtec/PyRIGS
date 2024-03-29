# Generated by Django 3.2.11 on 2022-01-25 12:58

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('training', '0002_alter_traininglevel_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='trainingcategory',
            name='training_level',
            field=models.ForeignKey(help_text='If this is set, any user with the selected level may pass out users within this category, regardless of other status', null=True, on_delete=django.db.models.deletion.CASCADE, to='training.traininglevel'),
        ),
    ]

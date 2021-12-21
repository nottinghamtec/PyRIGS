# Generated by Django 3.1.13 on 2021-12-21 15:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('training', '0008_trainingitem_active'),
    ]

    operations = [
        migrations.AlterField(
            model_name='trainingcategory',
            name='reference_number',
            field=models.CharField(max_length=3, unique=True),
        ),
        migrations.AlterUniqueTogether(
            name='trainingitem',
            unique_together={('reference_number', 'active', 'category')},
        ),
    ]

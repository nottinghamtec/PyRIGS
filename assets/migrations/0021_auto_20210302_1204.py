# Generated by Django 3.1.7 on 2021-03-02 12:04

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('assets', '0020_auto_20210302_1201'),
    ]

    operations = [
        migrations.AlterField(
            model_name='assetstatus',
            name='display_class',
            field=models.CharField(blank=True, default='', help_text='HTML class to be appended to alter display of assets with this status, such as in the list.', max_length=80),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='cabletype',
            name='plug',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='plug', to='assets.connector'),
        ),
        migrations.AlterField(
            model_name='cabletype',
            name='socket',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='socket', to='assets.connector'),
        ),
        migrations.AlterField(
            model_name='supplier',
            name='address',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AlterField(
            model_name='supplier',
            name='email',
            field=models.EmailField(blank=True, default='', max_length=254),
        ),
        migrations.AlterField(
            model_name='supplier',
            name='notes',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AlterField(
            model_name='supplier',
            name='phone',
            field=models.CharField(blank=True, default='', max_length=15),
        ),
    ]

# Generated by Django 3.2.19 on 2023-05-20 10:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('RIGS', '0048_auto_20230518_1256'),
    ]

    operations = [
        migrations.AlterField(
            model_name='powertestrecord',
            name='fd_earth_fault',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Earth Fault Loop Impedance (Z<small>S</small>) / Ω', max_digits=5, null=True, verbose_name='Earth Fault Loop Impedance'),
        ),
        migrations.AlterField(
            model_name='powertestrecord',
            name='fd_pssc',
            field=models.IntegerField(blank=True, help_text='Prospective Short Circuit Current / A', null=True, verbose_name='PSCC'),
        ),
        migrations.AlterField(
            model_name='powertestrecord',
            name='w1_earth_fault',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Earth Fault Loop Impedance (Z<small>S</small>) / Ω', max_digits=5, null=True, verbose_name='Earth Fault Loop Impedance'),
        ),
        migrations.AlterField(
            model_name='powertestrecord',
            name='w1_voltage',
            field=models.IntegerField(blank=True, help_text='Voltage / V', null=True),
        ),
        migrations.AlterField(
            model_name='powertestrecord',
            name='w2_earth_fault',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Earth Fault Loop Impedance (Z<small>S</small>) / Ω', max_digits=5, null=True, verbose_name='Earth Fault Loop Impedance'),
        ),
        migrations.AlterField(
            model_name='powertestrecord',
            name='w2_voltage',
            field=models.IntegerField(blank=True, help_text='Voltage / V', null=True),
        ),
        migrations.AlterField(
            model_name='powertestrecord',
            name='w3_earth_fault',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Earth Fault Loop Impedance (Z<small>S</small>) / Ω', max_digits=5, null=True, verbose_name='Earth Fault Loop Impedance'),
        ),
        migrations.AlterField(
            model_name='powertestrecord',
            name='w3_voltage',
            field=models.IntegerField(blank=True, help_text='Voltage / V', null=True),
        ),
    ]

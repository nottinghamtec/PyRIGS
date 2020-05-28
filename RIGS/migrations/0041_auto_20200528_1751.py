# Generated by Django 3.0.3 on 2020-05-28 16:51

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('RIGS', '0040_delete_rigsversion'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='event',
            name='risk_assessment_edit_url',
        ),
        migrations.CreateModel(
            name='RiskAssessment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(blank=True, null=True)),
                ('last_edited', models.DateTimeField(blank=True, null=True)),
                ('nonstandard_equipment', models.BooleanField(default=False)),
                ('nonstandard_use', models.BooleanField(default=False)),
                ('contractors', models.BooleanField(default=False)),
                ('other_companies', models.BooleanField(default=False)),
                ('crew_fatigue', models.BooleanField(default=False)),
                ('general_notes', models.TextField(blank=True, null=True)),
                ('big_power', models.BooleanField(default=False)),
                ('generators', models.BooleanField(default=False)),
                ('other_companies_power', models.BooleanField(default=False)),
                ('nonstandard_equipment_power', models.BooleanField(default=False)),
                ('multiple_electrical_environments', models.BooleanField(default=False)),
                ('power_notes', models.TextField(blank=True, null=True)),
                ('noise_monitoring', models.BooleanField(default=False)),
                ('sound_notes', models.TextField(blank=True, null=True)),
                ('known_venue', models.BooleanField(default=False)),
                ('safe_loading', models.BooleanField(default=False)),
                ('safe_storage', models.BooleanField(default=False)),
                ('area_outside_of_control', models.BooleanField(default=False)),
                ('barrier_required', models.BooleanField(default=False)),
                ('nonstandard_emergency_procedure', models.BooleanField(default=False)),
                ('special_structures', models.BooleanField(default=False)),
                ('persons_responsible_structures', models.TextField(blank=True, null=True)),
                ('suspended_structures', models.BooleanField(default=False)),
                ('completed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='completer', to=settings.AUTH_USER_MODEL, verbose_name='Completed By')),
                ('power_mic', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='power_mic', to=settings.AUTH_USER_MODEL, verbose_name='Power MIC')),
            ],
        ),
        migrations.AddField(
            model_name='event',
            name='risk_assessment',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='RIGS.RiskAssessment'),
        ),
    ]

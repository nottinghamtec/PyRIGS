# Generated by Django 3.1.5 on 2021-06-30 14:14

import RIGS.models
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('training', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='TrainingItemQualification',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('depth', models.IntegerField(choices=[(0, 'Training Started'), (1, 'Training Complete'), (2, 'Passed Out')])),
                ('date', models.DateTimeField()),
                ('notes', models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name='TrainingLevel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('department', models.CharField(max_length=50, null=True)),
                ('level', models.IntegerField(choices=[(0, 'Technical Assistant'), (1, 'Technician'), (2, 'Supervisor')])),
            ],
            bases=(models.Model, RIGS.models.RevisionMixin),
        ),
        migrations.CreateModel(
            name='TrainingLevelQualification',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('confirmed_on', models.DateTimeField()),
                ('confirmed_by', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, related_name='confirmer', to='training.trainee')),
                ('level', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to='training.traininglevel')),
                ('trainee', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, related_name='levels', to='training.trainee')),
            ],
        ),
        migrations.RemoveField(
            model_name='supervisor',
            name='department',
        ),
        migrations.RemoveField(
            model_name='supervisor',
            name='requirements',
        ),
        migrations.RemoveField(
            model_name='technicalassistant',
            name='requirements',
        ),
        migrations.RemoveField(
            model_name='technician',
            name='department',
        ),
        migrations.RemoveField(
            model_name='technician',
            name='requirements',
        ),
        migrations.RemoveField(
            model_name='trainingiteminstance',
            name='item',
        ),
        migrations.RemoveField(
            model_name='trainingiteminstance',
            name='passed_out_by',
        ),
        migrations.RemoveField(
            model_name='trainingiteminstance',
            name='trainee',
        ),
        migrations.RemoveField(
            model_name='trainingiteminstance',
            name='training_complete_by',
        ),
        migrations.RemoveField(
            model_name='trainingiteminstance',
            name='training_started_by',
        ),
        migrations.AlterField(
            model_name='trainingitem',
            name='category',
            field=models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to='training.trainingcategory'),
        ),
        migrations.DeleteModel(
            name='Department',
        ),
        migrations.DeleteModel(
            name='Supervisor',
        ),
        migrations.DeleteModel(
            name='TechnicalAssistant',
        ),
        migrations.DeleteModel(
            name='Technician',
        ),
        migrations.DeleteModel(
            name='TrainingItemInstance',
        ),
        migrations.AddField(
            model_name='trainingitemqualification',
            name='item',
            field=models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to='training.trainingitem'),
        ),
        migrations.AddField(
            model_name='trainingitemqualification',
            name='supervisor',
            field=models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, related_name='training_started', to='training.trainee'),
        ),
        migrations.AddField(
            model_name='trainingitemqualification',
            name='trainee',
            field=models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, related_name='items', to='training.trainee'),
        ),
    ]

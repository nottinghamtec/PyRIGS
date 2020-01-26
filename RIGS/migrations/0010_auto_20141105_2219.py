# -*- coding: utf-8 -*-


from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):
    dependencies = [
        ('RIGS', '0009_auto_20141105_1916'),
    ]

    operations = [
        migrations.CreateModel(
            name='EventCrew',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, verbose_name='ID', serialize=False)),
                ('rig', models.BooleanField(default=False)),
                ('run', models.BooleanField(default=False)),
                ('derig', models.BooleanField(default=False)),
                ('notes', models.TextField(blank=True, null=True)),
                ('event', models.ForeignKey(related_name='crew', to='RIGS.Event', on_delete=models.CASCADE)),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='event',
            name='collector',
            field=models.CharField(max_length=255, blank=True, null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='eventitem',
            name='event',
            field=models.ForeignKey(related_name='items', to='RIGS.Event', on_delete=models.CASCADE),
            preserve_default=True,
        ),
    ]

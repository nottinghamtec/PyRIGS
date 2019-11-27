# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('RIGS', '0002_modelcomment_person'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='modelcomment',
            name='user',
        ),
        migrations.RemoveField(
            model_name='person',
            name='comments',
        ),
        migrations.DeleteModel(
            name='ModelComment',
        ),
        migrations.AddField(
            model_name='person',
            name='notes',
            field=models.TextField(null=True, blank=True),
            preserve_default=True,
        ),
    ]

# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('RIGS', '0014_auto_20141208_0220'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='event',
            options={'permissions': (('view_event', 'Can view Events'),)},
        ),
        migrations.AlterModelOptions(
            name='organisation',
            options={'permissions': (('view_organisation', 'Can view Organisations'),)},
        ),
        migrations.AlterModelOptions(
            name='person',
            options={'permissions': (('view_person', 'Can view Persons'),)},
        ),
        migrations.AlterModelOptions(
            name='venue',
            options={'permissions': (('view_venue', 'Can view Venues'),)},
        ),
    ]

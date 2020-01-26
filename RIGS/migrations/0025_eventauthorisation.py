# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('RIGS', '0024_auto_20160229_2042'),
    ]

    operations = [
        migrations.CreateModel(
            name='EventAuthorisation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('email', models.EmailField(max_length=254)),
                ('name', models.CharField(max_length=255)),
                ('uni_id', models.CharField(max_length=10, null=True, verbose_name=b'University ID', blank=True)),
                ('account_code', models.CharField(max_length=50, null=True, blank=True)),
                ('amount', models.DecimalField(verbose_name=b'authorisation amount', max_digits=10, decimal_places=2)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('event', models.ForeignKey(related_name='authroisations', to='RIGS.Event', on_delete=models.CASCADE)),
            ],
        ),
    ]

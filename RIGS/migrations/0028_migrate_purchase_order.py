# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.db.models import F, Sum, DecimalField


def POs_forward(apps, schema_editor):
    VatRate = apps.get_model('RIGS', 'VatRate')
    Event = apps.get_model('RIGS', 'Event')
    EventItem = apps.get_model('RIGS', 'EventItem')
    EventAuthorisation = apps.get_model('RIGS', 'EventAuthorisation')
    db_alias = schema_editor.connection.alias
    for event in Event.objects.using(db_alias).filter(purchase_order__isnull=False):
        sum_total = EventItem.objects.filter(event=event).aggregate(
            sum_total=Sum(models.F('cost') * F('quantity'),
                          output_field=DecimalField(
                              max_digits=10,
                              decimal_places=2)
                          )
        )['sum_total']

        vat = VatRate.objects.using(db_alias).filter(start_at__lte=event.start_date).latest()
        total = sum_total + sum_total * vat.rate

        EventAuthorisation.objects.using(db_alias).create(event=event, name='LEGACY',
                                                          email='treasurer@nottinghamtec.co.uk',
                                                          amount=total)


def POs_reverse(apps, schema_editor):
    EventAuthorisation = apps.get_model('RIGS', 'EventAuthorisation')
    db_alias = schema_editor.connection.alias
    for auth in EventAuthorisation.objects.using(db_alias).filter(po__isnull=False):
        auth.event.purchase_order = auth.po
        auth.delete()


class Migration(migrations.Migration):
    dependencies = [
        ('RIGS', '0027_eventauthorisation_event_singular'),
    ]

    operations = [
        migrations.RunPython(POs_forward, POs_reverse),
        migrations.RemoveField(model_name='event', name='purchase_order')
    ]

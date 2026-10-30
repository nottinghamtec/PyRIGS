import datetime

from django.db import migrations, models
from django.db.models import Q

PROVISIONAL = 0


def mark_existing_responses_sent(apps, schema_editor):
    """Only current provisional events are still waiting on a response, so don't flag everything else"""
    Event = apps.get_model("RIGS", "Event")
    today = datetime.date.today()
    Event.objects.exclude(status=PROVISIONAL).update(default_response_sent=True)
    Event.objects.filter(status=PROVISIONAL).filter(
        Q(end_date__lt=today) | Q(end_date__isnull=True, start_date__lt=today)
    ).update(default_response_sent=True)


class Migration(migrations.Migration):

    dependencies = [
        ('RIGS', '0058_normalise_initials'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='kanban_finance',
            field=models.BooleanField(default=True, verbose_name='Show invoice columns on the Kanban'),
        ),
        migrations.AddField(
            model_name='event',
            name='default_response_sent',
            field=models.BooleanField(default=False, help_text='Has the client been sent our default response to their request?'),
        ),
        migrations.RunPython(mark_existing_responses_sent, migrations.RunPython.noop),
    ]

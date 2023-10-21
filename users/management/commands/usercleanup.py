from datetime import datetime, timedelta
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from RIGS.models import Profile
from training.models import TrainingLevel


# This is triggered nightly by Heroku Scheduler
class Command(BaseCommand):
    help = 'Performs perodic user maintenance tasks'

    def handle(self, *args, **options):
        for person in Profile.objects.all():
            # Inactivate users that have not logged in for a year
            if person.last_login is not None and (timezone.now() - person.last_login).days > 365:
                person.is_active = False
                person.is_approved = False
                person.save()
            # Ensure everyone with a supervisor level has the flag correctly set in the database
            if person.level_qualifications.exclude(confirmed_on=None).select_related('level') \
                    .filter(level__level__gte=TrainingLevel.SUPERVISOR) \
                    .exclude(level__department=TrainingLevel.HAULAGE) \
                    .exclude(level__department__isnull=True).exists():
                person.is_supervisor = True
                person.save()

import datetime
import random

from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from reversion import revisions as reversion

from training import models
from RIGS.models import Profile


class Command(BaseCommand):
    help = 'Adds training users'
    can_import_settings = True

    profiles = []
    committee_group = None

    def handle(self, *args, **options):
        print("Generating useful training users")
        from django.conf import settings

        if not (settings.DEBUG or settings.STAGING):
            raise CommandError('You cannot run this command in production')

        random.seed('otherwise it is done by time, which could lead to inconsistent tests')

        with transaction.atomic():
            self.setup_groups()
            self.setup_useful_profiles()
        print("Done generating useful training users")

    def setup_groups(self):
        self.committee_group = Group.objects.create(name='Committee')

        perms = [
            "add_trainingitemqualification",
            "change_trainingitemqualification",
            "delete_trainingitemqualification",
            "add_traininglevelqualification",
            "change_traininglevelqualification",
            "delete_traininglevelqualification",
            "add_traininglevelrequirement",
            "change_traininglevelrequirement",
            "delete_traininglevelrequirement"]

        for permId in perms:
            self.committee_group.permissions.add(Permission.objects.get(codename=permId))

        self.committee_group.save()

    def setup_useful_profiles(self):
        supervisor = Profile.objects.create(username="supervisor", first_name="Super", last_name="Visor",
                                            initials="SV",
                                            email="supervisor@example.com", is_active=True,
                                            is_staff=True, is_approved=True, is_supervisor=True)
        supervisor.set_password('supervisor')
        supervisor.groups.add(Group.objects.get(name="Keyholders"))
        supervisor.save()
        models.TrainingLevelQualification.objects.create(
            trainee=supervisor,
            level=models.TrainingLevel.objects.filter(
                level__gte=models.TrainingLevel.SUPERVISOR).exclude(
                department=models.TrainingLevel.HAULAGE).exclude(
                department__isnull=True).first(),
            confirmed_on=timezone.now(),
            confirmed_by=models.Trainee.objects.first())

        committee_user = Profile.objects.create(username="committee", first_name="Committee", last_name="Member",
                                                initials="CM",
                                                email="committee@example.com", is_active=True, is_approved=True)
        committee_user.groups.add(self.committee_group)
        supervisor.groups.add(Group.objects.get(name="Keyholders"))
        committee_user.set_password('committee')
        committee_user.save()

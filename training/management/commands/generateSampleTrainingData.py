import datetime
import random

from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from reversion import revisions as reversion

from training import models


class Command(BaseCommand):
    help = 'Adds sample data to use for testing'
    can_import_settings = True

    categories = []
    items = []
    levels = []

    def handle(self, *args, **options):
        print("Generating training data")
        from django.conf import settings

        if not (settings.DEBUG or settings.STAGING):
            raise CommandError('You cannot run this command in production')

        random.seed('otherwise it is done by time, which could lead to inconsistant tests')

        with transaction.atomic():
            self.setup_categories()
            self.setup_items()
            self.setup_levels()
            self.setup_supervisor()
        print("Done generating training data")

    def setup_categories(self):
        names = [(1, "Basic"), (2, "Sound"), (3, "Lighting"), (4, "Rigging"), (5, "Power"), (6, "Haulage")]

        for i, name in names:
            category = models.TrainingCategory.objects.create(reference_number=i, name=name)
            category.save()
            self.categories.append(category)

    def setup_items(self):
        names = ["Motorised Power Towers", "Catering", "Forgetting Cables", "Gazebo Construction", "Balanced Audio", "Unbalanced Audio", "BBQ/Bin Interactions", "Pushing Boxes", "How Not To Die", "Setting up projectors", "Basketing truss", "First Aid", "Digging Trenches", "Avoiding Bin Lorries", "Getting cherry pickers stuck in mud", "Crashing the Van", "Getting pigs to fly", "Basketing picnics", "Python programming", "Building Cables", "Unbuilding Cables", "Cat Herding", "Pancake making", "Tidying up", "Reading Manuals", "Bikeshedding"]

        for i,name in enumerate(names):
            item = models.TrainingItem.objects.create(category=random.choice(self.categories), reference_number=random.randint(0, 100), name=name)
            self.items.append(item)

    def setup_levels(self):
        self.levels.append(models.TrainingLevel.objects.create(level=models.TrainingLevel.TA, description="Passion will hatred faithful evil suicide noble battle. Truth aversion gains grandeur noble. Dead play gains prejudice god ascetic grandeur zarathustra dead good. Faithful ultimate justice overcome love will mountains inexpedient."))
        for i,name in models.TrainingLevel.DEPARTMENTS:
            technician = models.TrainingLevel.objects.create(level=models.TrainingLevel.TECHNICIAN, department=i, description="Moral pinnacle derive ultimate war dead. Strong fearful joy contradict battle christian faithful enlightenment prejudice zarathustra moral.")
            supervisor = models.TrainingLevel.objects.create(level=models.TrainingLevel.SUPERVISOR, department=i, description="Spirit holiest merciful mountains inexpedient reason value. Suicide ultimate hope.")
            supervisor.prerequisite_levels.add(technician)
            items = self.items.copy()
            for i in range(0, 30):
                if len(items) == 0:
                    break
                item = random.choice(items)
                items.remove(item)
                if i % 3 == 0:
                    models.TrainingLevelRequirement.objects.create(level=technician, item=item, depth=random.choice(models.TrainingItemQualification.CHOICES)[0])
                else:
                    models.TrainingLevelRequirement.objects.create(level=supervisor, item=item, depth=random.choice(models.TrainingItemQualification.CHOICES)[0])
            self.levels.append(technician)
            self.levels.append(supervisor)

    def setup_supervisor(self):
        supervisor = models.Profile.objects.create(username="supervisor", first_name="Super", last_name="Visor",
                                                   initials="SV",
                                                   email="supervisor@example.com", is_active=True,
                                                   is_staff=True)
        supervisor.set_password('supervisor')
        supervisor.save()
        models.TrainingLevelQualification.objects.create(trainee=supervisor, level=self.levels[-1], confirmed_on=timezone.now())

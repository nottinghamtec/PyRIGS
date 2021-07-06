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

    def handle(self, *args, **options):
        from django.conf import settings

        if not (settings.DEBUG or settings.STAGING):
            raise CommandError('You cannot run this command in production')

        random.seed('otherwise it is done by time, which could lead to inconsistant tests')

        with transaction.atomic():
            self.setup_categories()
            self.setup_items()
            self.setup_levels()

    def setup_categories(self):
        names = [(1, "Basic"), (2, "Sound"), (3, "Lighting"), (4, "Rigging"), (5, "Power"), (6, "Haulage")]
        
        for i, name in names:
            category = models.TrainingCategory.objects.create(reference_number=i, name=name)
            category.save()
            self.categories.append(category)

    def setup_items(self):
        names = ["Motorised Power Towers", "Catering", "Forgetting Cables", "Gazebo Construction", "Balanced Audio", "Unbalanced Audio", "BBQ/Bin Interactions", "Pushing Boxes", "How Not To Die", "Setting up projectors", "Basketing truss", "First Aid", "Digging Trenches", "Avoiding Bin Lorries", "Getting cherry pickers stuck in mud", "Crashing the Van"]
        
        for i,name in enumerate(names):
            item = models.TrainingItem.objects.create(category=random.choice(self.categories), reference_number=random.randint(0, 100), name=name)
            self.items.append(item)

    def setup_levels(self):
        pass

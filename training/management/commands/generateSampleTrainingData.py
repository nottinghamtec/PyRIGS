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
        names = ["Motorised Power Towers", "Catering", "Forgetting Cables", "Gazebo Construction", "Balanced Audio", "Unbalanced Audio", "BBQ/Bin Interactions", "Pushing Boxes", "How Not To Die", "Setting up projectors", "Basketing truss", "First Aid", "Digging Trenches", "Avoiding Bin Lorries", "Getting cherry pickers stuck in mud", "Crashing the Van", "Getting pigs to fly", "Basketing picnics", "Python programming", "Building Cables", "Unbuilding Cables", "Cat Herding", "Pancake making", "Tidying up", "Reading Manuals", "Bikeshedding", "DJing", "Partying", "Teccie Gym", "Putting dust covers on", "Cleaning Lights", "Water Skiing", "Drinking", "Fundamentals of Audio", "Fundamentals of Photons", "Social Interaction", "Discourse Searching", "Discord Searching", "Coiling Cables", "Kit Amnesties", "Van Insurance", "Subhire Insurance", "Paperwork", "More Paperwork", "Second Aid", "Being Old", "Maxihoists", "Sleazyhoists", "Telehoists", "Prolyte", "Prolights", "Making Phonecalls", "Quoting For A Rig", "Basic MIC", "Advanced MIC", "Avoiding MIC", "Washing Cables", "Cable Ramp", "Van Loading", "Trailer Loading", "Storeroom Loading", "Welding", "Fire Extinguishers", "Boring Conference AV", "Flyaway", "Short Leads", "RF Systems", "QLab", "Use of Ladders", "Working at Height", "Organising Training", "Organising Organising Training Training", "Mental Health First Aid", "Writing RAMS", "Makros Runs", "PAT", "Kit Fixing", "Kit Breaking", "Replacing Lamps", "Flying Pig Systems", "Procrastination", "Drinking Beer", "Sending Emails", "Email Signatures", "Digital Sound Desks", "Digital Lighting Desks", "Painting PS10s", "Chain Lubrication", "Big Power", "BIGGER POWER", "Pixel Mapping", "RDM", "Ladder Inspections", "Losing Crimpaz", "Scrapping Trilite", "Bin Diving", "Wiki Editing"]

        for i,name in enumerate(names):
            item = models.TrainingItem.objects.create(category=random.choice(self.categories), reference_number=random.randint(0, 100), name=name)
            self.items.append(item)

    def setup_levels(self):
        items = self.items.copy()
        ta = models.TrainingLevel.objects.create(level=models.TrainingLevel.TA, description="Passion will hatred faithful evil suicide noble battle. Truth aversion gains grandeur noble. Dead play gains prejudice god ascetic grandeur zarathustra dead good. Faithful ultimate justice overcome love will mountains inexpedient.")
        self.levels.append(ta)
        tech_ccs = models.TrainingLevel.objects.create(level=models.TrainingLevel.TECHNICIAN, description="Technician Common Competencies. Spirit abstract endless insofar horror sexuality depths war decrepit against strong aversion revaluation free. Christianity reason joy sea law mountains transvaluation. Sea battle aversion dead ultimate morality self. Faithful morality.")
        tech_ccs.prerequisite_levels.add(ta)
        super_ccs = models.TrainingLevel.objects.create(level=models.TrainingLevel.SUPERVISOR, description="Depths disgust hope faith of against hatred will victorious. Law...")
        for i in range(0, 5):
                if len(items) == 0:
                    break
                item = random.choice(items)
                items.remove(item)
                if i % 3 == 0:
                    models.TrainingLevelRequirement.objects.create(level=tech_ccs, item=item, depth=random.choice(models.TrainingItemQualification.CHOICES)[0])
                else:
                    models.TrainingLevelRequirement.objects.create(level=super_ccs, item=item, depth=random.choice(models.TrainingItemQualification.CHOICES)[0])
        for i,name in models.TrainingLevel.DEPARTMENTS:
            technician = models.TrainingLevel.objects.create(level=models.TrainingLevel.TECHNICIAN, department=i, description="Moral pinnacle derive ultimate war dead. Strong fearful joy contradict battle christian faithful enlightenment prejudice zarathustra moral.")
            technician.prerequisite_levels.add(tech_ccs)
            supervisor = models.TrainingLevel.objects.create(level=models.TrainingLevel.SUPERVISOR, department=i, description="Spirit holiest merciful mountains inexpedient reason value. Suicide ultimate hope.")
            supervisor.prerequisite_levels.add(super_ccs, technician)

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
        models.TrainingLevelQualification.objects.create(trainee=supervisor, level=models.TrainingLevel.objects.filter(level__gte=models.TrainingLevel.SUPERVISOR).exclude(department=models.TrainingLevel.HAULAGE).first(), confirmed_on=timezone.now())

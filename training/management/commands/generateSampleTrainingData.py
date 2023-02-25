import datetime
import random

from django.contrib.auth.models import Group, Permission
from django.core.management import call_command
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
        # call_command('generate_sample_training_users')
        print("Done generating training data")

    def setup_categories(self):
        names = [(1, "Basic"), (2, "Sound"), (3, "Lighting"), (4, "Rigging"), (5, "Power"), (6, "Haulage")]

        for i, name in names:
            category = models.TrainingCategory.objects.create(reference_number=i, name=name)
            category.save()
            self.categories.append(category)

    def setup_items(self):
        names = [
            "Motorised Power Towers",
            "Catering",
            "Forgetting Cables",
            "Gazebo Construction",
            "Balanced Audio",
            "Unbalanced Audio",
            "BBQ/Bin Interactions",
            "Pushing Boxes",
            "How Not To Die",
            "Setting up projectors",
            "Basketing truss",
            "First Aid",
            "Digging Trenches",
            "Avoiding Bin Lorries",
            "Getting cherry pickers stuck in mud",
            "Crashing the Van",
            "Getting pigs to fly",
            "Basketing picnics",
            "Python programming",
            "Building Cables",
            "Unbuilding Cables",
            "Cat Herding",
            "Pancake making",
            "Tidying up",
            "Reading Manuals",
            "Bikeshedding",
            "DJing",
            "Partying",
            "Teccie Gym",
            "Putting dust covers on",
            "Cleaning Lights",
            "Water Skiing",
            "Drinking",
            "Fundamentals of Audio",
            "Fundamentals of Photons",
            "Social Interaction",
            "Discourse Searching",
            "Discord Searching",
            "Coiling Cables",
            "Kit Amnesties",
            "Van Insurance",
            "Subhire Insurance",
            "Paperwork",
            "More Paperwork",
            "Second Aid",
            "Being Old",
            "Maxihoists",
            "Sleazyhoists",
            "Telehoists",
            "Prolyte",
            "Prolights",
            "Making Phonecalls",
            "Quoting For A Rig",
            "Basic MIC",
            "Advanced MIC",
            "Avoiding MIC",
            "Washing Cables",
            "Cable Ramp",
            "Van Loading",
            "Trailer Loading",
            "Storeroom Loading",
            "Welding",
            "Fire Extinguishers",
            "Boring Conference AV",
            "Flyaway",
            "Short Leads",
            "RF Systems",
            "QLab",
            "Use of Ladders",
            "Working at Height",
            "Organising Training",
            "Organising Organising Training Training",
            "Mental Health First Aid",
            "Writing RAMS",
            "Makros Runs",
            "PAT",
            "Kit Fixing",
            "Kit Breaking",
            "Replacing Lamps",
            "Flying Pig Systems",
            "Procrastination",
            "Drinking Beer",
            "Sending Emails",
            "Email Signatures",
            "Digital Sound Desks",
            "Digital Lighting Desks",
            "Painting PS10s",
            "Chain Lubrication",
            "Big Power",
            "BIGGER POWER",
            "Pixel Mapping",
            "RDM",
            "Ladder Inspections",
            "Losing Crimpaz",
            "Scrapping Trilite",
            "Bin Diving",
            "Wiki Editing"]

        descriptions = [
            "Physical training concentrates on mechanistic goals: training programs in this area develop specific motor skills, agility, strength or physical fitness, often with an intention of peaking at a particular time.",
            "In military use, training means gaining the physical ability to perform and survive in combat, and learn the many skills needed in a time of war.",
            "These include how to use a variety of weapons, outdoor survival skills, and how to survive being captured by the enemy, among many others.  See military education and training.",
            "While some studies have indicated relaxation training is useful for some medical conditions, autogenic training has limited results or has been the result of few studies.",
            "Some occupations are inherently hazardous, and require a minimum level of competence before the practitioners can perform the work at an acceptable level of safety to themselves or others in the vicinity.",
            "Occupational diving, rescue, firefighting and operation of certain types of machinery and vehicles may require assessment and certification of a minimum acceptable competence before the person is allowed to practice as a licensed instructor."
        ]

        for i, name in enumerate(names):
            category = random.choice(self.categories)
            previous_item = models.TrainingItem.objects.filter(category=category).last()
            if previous_item is not None:
                number = previous_item.reference_number + 1
            else:
                number = 0
            item = models.TrainingItem.objects.create(category=category, reference_number=number, name=name, description=random.choice(descriptions) + random.choice(descriptions) + random.choice(descriptions))
            self.items.append(item)

    def setup_levels(self):
        items = self.items.copy()
        ta = models.TrainingLevel.objects.create(
            level=models.TrainingLevel.TA,
            description="Passion will hatred faithful evil suicide noble battle. Truth aversion gains grandeur noble. Dead play gains prejudice god ascetic grandeur zarathustra dead good. Faithful ultimate justice overcome love will mountains inexpedient.",
            icon="address-card")
        self.levels.append(ta)
        tech_ccs = models.TrainingLevel.objects.create(
            level=models.TrainingLevel.TECHNICIAN,
            description="Technician Common Competencies. Spirit abstract endless insofar horror sexuality depths war decrepit against strong aversion revaluation free. Christianity reason joy sea law mountains transvaluation. Sea battle aversion dead ultimate morality self. Faithful morality.",
            icon="book-reader")
        tech_ccs.prerequisite_levels.add(ta)
        super_ccs = models.TrainingLevel.objects.create(level=models.TrainingLevel.SUPERVISOR, description="Depths disgust hope faith of against hatred will victorious. Law...", icon="user-graduate")
        for i in range(0, 5):
            if len(items) == 0:
                break
            item = random.choice(items)
            items.remove(item)
            if i % 3 == 0:
                models.TrainingLevelRequirement.objects.create(level=tech_ccs, item=item, depth=random.choice(models.TrainingItemQualification.CHOICES)[0])
            else:
                models.TrainingLevelRequirement.objects.create(level=super_ccs, item=item, depth=random.choice(models.TrainingItemQualification.CHOICES)[0])
        icons = {
            models.TrainingLevel.SOUND: ('microphone', 'microphone-alt'),
            models.TrainingLevel.LIGHTING: ('lightbulb', 'traffic-light'),
            models.TrainingLevel.POWER: ('plug', 'bolt'),
            models.TrainingLevel.RIGGING: ('link', 'pallet'),
            models.TrainingLevel.HAULAGE: ('truck', 'route'),
        }
        for i, name in models.TrainingLevel.DEPARTMENTS:
            technician = models.TrainingLevel.objects.create(level=models.TrainingLevel.TECHNICIAN, department=i, description="Moral pinnacle derive ultimate war dead. Strong fearful joy contradict battle christian faithful enlightenment prejudice zarathustra moral.", icon=icons[i][0])
            technician.prerequisite_levels.add(tech_ccs)
            supervisor = models.TrainingLevel.objects.create(level=models.TrainingLevel.SUPERVISOR, department=i, description="Spirit holiest merciful mountains inexpedient reason value. Suicide ultimate hope.", icon=icons[i][1])
            supervisor.prerequisite_levels.add(super_ccs, technician)

            for i in range(0, 30):
                if len(items) == 0:
                    break
                item = random.choice(items)
                items.remove(item)
                try:
                    if i % 3 == 0:
                        models.TrainingLevelRequirement.objects.create(level=technician, item=item, depth=random.choice(models.TrainingItemQualification.CHOICES)[0])
                    else:
                        models.TrainingLevelRequirement.objects.create(level=supervisor, item=item, depth=random.choice(models.TrainingItemQualification.CHOICES)[0])
                except:  # noqa
                    print("Failed create for {}. Weird.".format(item))

            self.levels.append(technician)
            self.levels.append(supervisor)

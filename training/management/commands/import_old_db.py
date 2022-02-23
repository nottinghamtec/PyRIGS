import os
import datetime
import re
import xml.etree.ElementTree as ET
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db.utils import IntegrityError
from django.utils.timezone import make_aware

from training import models
from RIGS.models import Profile


class Command(BaseCommand):
    epoch = datetime.date(1970, 1, 1)
    id_map = {}

    def handle(self, *args, **options):
        self.import_Trainees()
        self.import_TrainingCatagory()
        self.import_TrainingItem()
        self.import_TrainingItemQualification()
        self.import_TrainingLevel()
        self.import_TrainingLevelQualification()
        self.import_TrainingLevelRequirements()

    @staticmethod
    def xml_path(file):
        return os.path.join(settings.BASE_DIR, 'data/{}'.format(file))

    @staticmethod
    def parse_xml(file):
        tree = ET.parse(file)

        return tree.getroot()

    def import_Trainees(self):
        tally = [0, 0]

        root = self.parse_xml(self.xml_path('Members.xml'))

        for child in root:
            try:
                name = child.find('Member_x0020_Name').text
                first_name = name.split()[0]
                last_name = " ".join(name.split()[1:])
                profile = Profile.objects.filter(first_name=first_name, last_name=last_name).first()

                if profile:
                    self.id_map[child.find('ID').text] = profile.pk
                    print(f"Found existing user {profile}, matching data")
                    tally[0] += 1
                else:
                    # PYTHONIC, BABY
                    initials = first_name[0] + "".join([name_section[0] for name_section in re.split("\\s*-", last_name.replace("(", ""))])
                    # print(initials)
                    new_profile = Profile.objects.create(username=name.replace(" ", ""),
                                                         first_name=first_name,
                                                         last_name=last_name,
                                                         initials=initials)
                    self.id_map[child.find('ID').text] = new_profile.pk
                    tally[1] += 1
                    print(f"No match found, creating new user {new_profile}")
            except AttributeError:  # W.T.F
                print("Trainee #{} is FUBAR".format(child.find('ID').text))

        print('Trainees - Updated: {}, Created: {}'.format(tally[0], tally[1]))

    def import_TrainingCatagory(self):
        tally = [0, 0]

        root = self.parse_xml(self.xml_path('Categories.xml'))

        for child in root:
            obj, created = models.TrainingCategory.objects.update_or_create(
                pk=int(child.find('ID').text),
                reference_number=int(child.find('Category_x0020_Number').text),
                name=child.find('Category_x0020_Name').text
            )

            if created:
                tally[1] += 1
            else:
                tally[0] += 1

        print('Categories - Updated: {}, Created: {}'.format(tally[0], tally[1]))

    def import_TrainingItem(self):
        tally = [0, 0]

        root = self.parse_xml(self.xml_path('Training Items.xml'))

        for child in root:
            if child.find('active').text == '0':
                active = False
            else:
                active = True

            number = int(child.find('Item_x0020_Number').text)
            name = child.find('Item_x0020_Name').text
            category = models.TrainingCategory.objects.get(pk=int(child.find('Category_x0020_ID').text))

            try:
                obj, created = models.TrainingItem.objects.update_or_create(
                    pk=int(child.find('ID').text),
                    reference_number=number,
                    description=name,
                    category=category,
                    active=active
                )
            except IntegrityError:
                print(f"Training Item {category.reference_number}.{number} {name} has a duplicate reference number")

            if created:
                tally[1] += 1
            else:
                tally[0] += 1

        print(f'Training Items - Updated: {tally[0]}, Created: {tally[1]}')

    def import_TrainingItemQualification(self):
        tally = [0, 0, 0]

        root = self.parse_xml(self.xml_path('Training Records.xml'))

        for child in root:
            depths = [("Training_Started", models.TrainingItemQualification.STARTED),
                      ("Training_Complete", models.TrainingItemQualification.COMPLETE),
                      ("Competency_Assessed", models.TrainingItemQualification.PASSED_OUT), ]

            for (depth, depth_index) in depths:
                if child.find(f'{depth}_Date') is not None:
                    if child.find(f'{depth}_Assessor_ID') is None:
                        print(f"Training Record #{child.find('ID').text} had no supervisor. Assigning System User.")
                        supervisor = Profile.objects.get(first_name="God")
                        continue
                    supervisor = Profile.objects.get(pk=self.id_map[child.find('{}_Assessor_ID'.format(depth)).text])
                    if child.find('Member_ID') is None:
                        print("Training Record #{} didn't train anybody and has been ignored. Dammit {}".format(child.find('ID').text, supervisor.name))
                        tally[2] += 1
                        continue
                    try:
                        obj, created = models.TrainingItemQualification.objects.update_or_create(
                            item=models.TrainingItem.objects.get(pk=int(child.find('Training_Item_ID').text)),
                            trainee=Profile.objects.get(pk=self.id_map[child.find('Member_ID').text]),
                            depth=depth_index,
                            date=child.find('{}_Date'.format(depth)).text[:-9],  # Stored as datetime with time as midnight because fuck you I guess
                            supervisor=supervisor
                        )
                        notes = child.find('{}_Notes'.format(depth))
                        if notes is not None:
                            obj.notes = notes.text
                            obj.save()
                        if created:
                            tally[1] += 1
                        else:
                            tally[0] += 1
                    except IntegrityError:  # Eh?
                        print("Training Record #{} is probably duplicate. ಠ_ಠ".format(child.find('ID').text))
                    except AttributeError:
                        print(child.find('ID').text)

        print('Training Item Qualifications - Updated: {}, Created: {}, Broken: {}'.format(tally[0], tally[1], tally[2]))

    def import_TrainingLevel(self):
        tally = [0, 0]

        root = self.parse_xml(self.xml_path('Training Levels.xml'))

        for child in root:
            name = child.find('Level_x0020_Name').text
            if name == "Technical Assistant":
                level = models.TrainingLevel.TA
                depString = None
            elif "Common" in name:
                levelString = name.split()[0]
                if levelString == "Technician":
                    level = models.TrainingLevel.TECHNICIAN
                elif levelString == "Supervisor":
                    level = models.TrainingLevel.SUPERVISOR
                depString = None
            else:
                depString = name.split()[-1]
                levelString = name.split()[0]
                if levelString == "Technician":
                    level = models.TrainingLevel.TECHNICIAN
                elif levelString == "Supervisor":
                    level = models.TrainingLevel.SUPERVISOR
                else:
                    print(levelString)
                    continue
                for dep in models.TrainingLevel.DEPARTMENTS:
                    if dep[1] == depString:
                        department = dep[0]

            desc = ""
            if child.find('Desc') is not None:
                desc = child.find('Desc').text

            obj, created = models.TrainingLevel.objects.update_or_create(
                pk=int(child.find('ID').text),
                description=desc,
                level=level
            )
            if depString is not None:
                obj.department = department
                obj.save()

            if created:
                tally[1] += 1
            else:
                tally[0] += 1

        for level in models.TrainingLevel.objects.all():
            if level.department is not None:
                if level.level == models.TrainingLevel.TECHNICIAN:
                    level.prerequisite_levels.add(models.TrainingLevel.objects.get(level=models.TrainingLevel.TA), models.TrainingLevel.objects.get(level=models.TrainingLevel.TECHNICIAN, department=None))
                elif level.level == models.TrainingLevel.SUPERVISOR:
                    level.prerequisite_levels.add(models.TrainingLevel.objects.get(level=models.TrainingLevel.TECHNICIAN, department=level.department), models.TrainingLevel.objects.get(level=models.TrainingLevel.SUPERVISOR, department=None))

        print('Training Levels - Updated: {}, Created: {}'.format(tally[0], tally[1]))

    def import_TrainingLevelQualification(self):
        tally = [0, 0]

        root = self.parse_xml(self.xml_path('Training Level Records.xml'))

        for child in root:
            try:
                trainee = Profile.objects.get(pk=self.id_map[child.find('Member_x0020_ID').text]) if child.find('Member_x0020_ID') is not None else False
                level = models.TrainingLevel.objects.get(pk=int(child.find('Training_x0020_Level_x0020_ID').text)) if child.find('Training_x0020_Level_x0020_ID') is not None else False

                if trainee and level:
                    obj, created = models.TrainingLevelQualification.objects.update_or_create(pk=int(child.find('ID').text),
                                                                                              trainee=trainee,
                                                                                              level=level)
                else:
                    print('Training Level Qualification #{} failed to import. Trainee: {} and Level: {}'.format(child.find('ID').text, trainee, level))
                    continue

                if child.find('Date_x0020_Level_x0020_Awarded') is not None:
                    obj.confirmed_on = make_aware(datetime.datetime.strptime(child.find('Date_x0020_Level_x0020_Awarded').text.split('T')[0], "%Y-%m-%d"))
                    obj.save()
                    # confirmed by?

                if created:
                    tally[1] += 1
                else:
                    tally[0] += 1
            except IntegrityError:  # Eh?
                print("Training Level Qualification #{} is duplicate. ಠ_ಠ".format(child.find('ID').text))

        print('TrainingLevelQualifications - Updated: {}, Created: {}'.format(tally[0], tally[1]))

    def import_TrainingLevelRequirements(self):
        tally = [0, 0]

        root = self.parse_xml(self.xml_path('Training Level Requirements.xml'))

        for child in root:
            items = child.find('Items').text.split(",")
            for item in items:
                try:
                    item = item.split('.')
                    obj, created = models.TrainingLevelRequirement.objects.update_or_create(
                        level=models.TrainingLevel.objects.get(
                            pk=int(
                                child.find('Level').text)), item=models.TrainingItem.objects.get(
                            active=True, reference_number=item[1], category=models.TrainingCategory.objects.get(
                                reference_number=item[0])), depth=int(
                            child.find('Depth').text))

                    if created:
                        tally[1] += 1
                    else:
                        tally[0] += 1
                except models.TrainingItem.DoesNotExist:
                    print("Item with number {} does not exist".format(item))
                except models.TrainingItem.MultipleObjectsReturned:
                    print(models.TrainingItem.objects.filter(reference_number=item[1], category=models.TrainingCategory.objects.get(reference_number=item[0])))

        print('TrainingLevelRequirements - Updated: {}, Created: {}'.format(tally[0], tally[1]))

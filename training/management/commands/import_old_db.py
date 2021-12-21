import os
import datetime
import re
import xml.etree.ElementTree as ET
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db.utils import IntegrityError

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
                    tally[0] += 1
                else:
                    # PYTHONIC, BABY
                    initials = first_name[0] + "".join([name_section[0] for name_section in re.split("\s*-", last_name.replace("(", ""))])
                    # print(initials)
                    new_profile = Profile.objects.create(username=name.replace(" ", ""),
                                           first_name=first_name,
                                           last_name=last_name,
                                           initials=initials)
                    self.id_map[child.find('ID').text] = new_profile.pk
                    tally[1] += 1
            except AttributeError: # W.T.F
                print("Trainee #{} is FUBAR".format(child.find('ID').text))

        print('Trainees - Updated: {}, Created: {}'.format(tally[0], tally[1]))

    def import_TrainingCatagory(self):
        tally = [0, 0]

        root = self.parse_xml(self.xml_path('Categories.xml'))

        for child in root:
            obj, created = models.TrainingCategory.objects.update_or_create(
                pk=int(child.find('ID').text),
                reference_number = int(child.find('Category_x0020_Number').text),
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
            if child.find('active').text == '0': active = False
            else: active =  True
            obj, created = models.TrainingItem.objects.update_or_create(
                pk = int(child.find('ID').text),
                reference_number = int(child.find('Item_x0020_Number').text),
                name = child.find('Item_x0020_Name').text,
                category = models.TrainingCategory.objects.get(pk=int(child.find('Category_x0020_ID').text)),
                active = active
            )

            if created:
                tally[1] += 1
            else:
                tally[0] += 1

        print('Training Items - Updated: {}, Created: {}'.format(tally[0], tally[1]))

    def import_TrainingItemQualification(self):
        tally = [0, 0, 0]

        root = self.parse_xml(self.xml_path('Training Records.xml'))

        for child in root:
            depths = [("Training_Started", models.TrainingItemQualification.STARTED),
                      ("Training_Complete", models.TrainingItemQualification.COMPLETE),
                      ("Competency_Assessed", models.TrainingItemQualification.PASSED_OUT)]
            for depth, depth_index in depths:
                if child.find('{}_Date'.format(depth)) is not None:
                    if child.find('{}_Assessor_ID'.format(depth)) is None:
                        print("Training Record #{} had no supervisor. Hmm.".format(child.find('ID').text))
                        tally[2] += 1
                        # TODO Assign God/Satan/Unknown here.
                        continue
                    supervisor = Profile.objects.get(pk=self.id_map[child.find('{}_Assessor_ID'.format(depth)).text])
                    if child.find('Member_ID') is None:
                        print("Training Record #{} didn't train anybody and has been ignored. Dammit {}".format(child.find('ID').text, supervisor.name))
                        tally[2] += 1
                        continue
                    try:
                        obj, created = models.TrainingItemQualification.objects.update_or_create(
                            pk=int(child.find('ID').text),
                            item = models.TrainingItem.objects.get(pk=int(child.find('Training_Item_ID').text)),
                            trainee = Profile.objects.get(pk=self.id_map[child.find('Member_ID').text]),
                            depth = depth_index,
                            date = child.find('{}_Date'.format(depth)).text[:-9], # Stored as datetime with time as midnight because fuck you I guess
                            supervisor = supervisor
                        )
                        notes = child.find('{}_Notes'.format(depth))
                        if notes:
                            obj.notes = notes.text
                            obj.save()
                        if created:
                            tally[1] += 1
                        else:
                            tally[0] += 1
                    except IntegrityError: # Eh?
                        print("Training Record #{} is duplicate. ಠ_ಠ".format(child.find('ID').text))
                    except AttributeError:
                        print(child.find('ID').text)

        print('Training Item Qualifications - Updated: {}, Created: {}, Broken: {}'.format(tally[0], tally[1], tally[2]))

    def import_TrainingLevel(self):
        tally = [0, 0]

        root = self.parse_xml(self.xml_path('Training Levels.xml'))

        for child in root:
            name = child.find('Level_x0020_Name').text
            if name != "Technical Assistant":
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
            else:
                level = models.TrainingLevel.TA
                depString = None

            desc = ""
            if child.find('Desc'):
                desc = child.find('Desc').text

            obj, created = models.TrainingLevel.objects.update_or_create(
                pk=int(child.find('ID').text),
                description = desc,
                level = level
            )
            if depString is not None:
                obj.department = department
                obj.save()

            if created:
                tally[1] += 1
            else:
                tally[0] += 1

        print('Training Levels - Updated: {}, Created: {}'.format(tally[0], tally[1]))

    def import_TrainingLevelQualification(self):
        tally = [0, 0]

        root = self.parse_xml(self.xml_path('Training Level Records.xml'))

        for child in root:
            try:
                if child.find('Training_x0020_Level_x0020_ID') is None:
                    print('Training Level Qualification #{} does not qualify in any level. How?'.format(child.find('ID').text))
                    continue
                if child.find('Member_x0020_ID') is None:
                    print('Training Level Qualification #{} does not qualify anyone. How?!'.format(child.find('ID').text))
                    continue
                obj, created = models.TrainingLevelQualification.objects.update_or_create(
                    pk = int(child.find('ID').text),
                    trainee = Profile.objects.get(pk=self.id_map[child.find('Member_x0020_ID').text]),
                    level = models.TrainingLevel.objects.get(pk=int(child.find('Training_x0020_Level_x0020_ID').text)),
                    # FIXME
                    #confirmed_on = child.find('Date_x0020_Level_x0020_Awarded').text
                    #confirmed by?
                )

                if created:
                    tally[1] += 1
                else:
                    tally[0] += 1
            except IntegrityError: # Eh?
                print("Training Level Qualification #{} is duplicate. ಠ_ಠ".format(child.find('ID').text))

        print('TrainingLevelQualifications - Updated: {}, Created: {}'.format(tally[0], tally[1]))

    def import_TrainingLevelRequirements(self):
        tally = [0, 0]

        root = self.parse_xml(self.xml_path('Training Level Requirements.xml'))

        for child in root:
            try:
                item = child.find('Item').text.split(".")
                obj, created = models.TrainingLevelRequirement.objects.update_or_create(level=models.TrainingLevel.objects.get(pk=int(child.find('Level').text)),item=models.TrainingItem.objects.get(reference_number=item[1], category=models.TrainingCategory.objects.get(reference_number=item[0])), depth=int(child.find('Depth').text))

                if created:
                    tally[1] += 1
                else:
                    tally[0] += 1
            except models.TrainingItem.DoesNotExist:
                print("Item with number {} does not exist".format(item))
            except models.TrainingItem.MultipleObjectsReturned:
                print(models.TrainingItem.objects.filter(reference_number=item[1], category=models.TrainingCategory.objects.get(reference_number=item[0])))

        print('TrainingLevelRequirements - Updated: {}, Created: {}'.format(tally[0], tally[1]))
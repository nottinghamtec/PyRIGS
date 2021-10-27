import os
import datetime
import xml.etree.ElementTree as ET
from django.core.management.base import BaseCommand
from django.conf import settings

from training import models

class Command(BaseCommand):
    epoch = datetime.date(1970, 1, 1)

    def handle(self, *args, **options):
        self.import_Trainee()
        self.import_TrainingCatagory()
        self.import_TrainingItem()
        self.import_TrainingItemQualification()
        self.import_TrainingLevel()
        self.import_TrainingLevelRequirement()
        self.import_TrainingLevelQualification()
        
    @staticmethod
    def xml_path(file):
        return os.path.join(settings.BASE_DIR, 'data/DB_Dump/{}'.format(file))

    @staticmethod
    def parse_xml(file):
        tree = ET.parse(file)

        return tree.getroot()

    def import_Trainee(self):
        tally = [0, 0]

        root = self.parse_xml(self.xml_path('Members.xml'))
        
        for child in root:
            obj, created = models.Trainee.objects.update_or_create(
                pk=int(child.find('ID').text)
                name = child.find('Member_x0020_Name').text
            )
        
            if created:
                tally[1] += 1
            else:
                tally[0] += 1
        
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
            obj, created = models.TrainingItem.objects.update_or_create(
                pk = int(child.find('ID').text),
                reference_number = int(child.find('Item_x0020_Number').text),
                name = child.find('Item_x0020_Name').text,
                category = int(child.find('Category_x0020_ID').text)
                #active?
            )
        
            if created:
                tally[1] += 1
            else:
                tally[0] += 1
        
        print('Training Items - Updated: {}, Created: {}'.format(tally[0], tally[1]))

    def import_TrainingItemQualification(self):
        tally = [0, 0]

        root = self.parse_xml(self.xml_path('Training Records.xml'))
        
        for child in root:
            if child.find('Traning_Started_Date').text != '':
                obj, created = models.TrainingItemQualification.objects.update_or_create(
                    pk=int(child.find('ID').text),
                    item = int(child.find('Training_Item_ID').text),
                    trainee = int(child.find('Member_ID').text),
                    depth = 0,
                    date = child.find('Traning_Started_Date').text,
                    supervisor = int(child.find('Training_Started_Assessor_ID'),text),
                    notes = child.find('Training_Started_Notes').text
                )
            if child.find('Traning_Complete_Date').text != '':
                obj, created = models.TrainingItemQualification.objects.update_or_create(
                    pk=int(child.find('ID').text),
                    item = int(child.find('Training_Item_ID').text),
                    trainee = int(child.find('Member_ID').text),
                    depth = 1,
                    date = child.find('Traning_Complete_Date').text,
                    supervisor = int(child.find('Training_Complete_Assessor_ID'),text),
                    notes = child.find('Training_Complete_Notes').text
                )
            if child.find('Competency_Assessed_Date').text != '':
                obj, created = models.TrainingItemQualification.objects.update_or_create(
                    pk=int(child.find('ID').text),
                    item = int(child.find('Training_Item_ID').text),
                    trainee = int(child.find('Member_ID').text),
                    depth = 2,
                    date = child.find('Competency_Assessed_Date').text,
                    supervisor = int(child.find('Competency_Assessed_Assessor_ID'),text),
                    notes = child.find('Competency_Assessed_Notes').text
                )
        
            if created:
                tally[1] += 1
            else:
                tally[0] += 1
        
        print('Training Item Qualifications - Updated: {}, Created: {}'.format(tally[0], tally[1]))

    def import_TrainingLevel(self):
        tally = [0, 0]

        root = self.parse_xml(self.xml_path('Training Levels'))
        
        for child in root:
            name = child.find('Level_x0020_Name').text
            if name != "Technical Assistant":
                depString = name.split()[-1]
                levelString = name.split()[0]
            else:
                levelString = name
                depString = None

            obj, created = models.TrainingLevel.objects.update_or_create(
                pk=int(child.find('ID').text),
                description = name,
                department = depString,
                level = levelString
            )
        
            if created:
                tally[1] += 1
            else:
                tally[0] += 1
        
        print('Training Levels - Updated: {}, Created: {}'.format(tally[0], tally[1])) 

    def import_TrainingLevelRequirement(self): #?
        tally = [0, 0]

        root = self.parse_xml(self.xml_path(''))
        
        for child in root:
            obj, created = models.TrainingLevelRequirement.objects.update_or_create(
                pk=int(child.find('ID').text)
            )
        
            if created:
                tally[1] += 1
            else:
                tally[0] += 1
        
        print('Training Level Requirements - Updated: {}, Created: {}'.format(tally[0], tally[1]))

    def import_TrainingLevelQualification(self):
        tally = [0, 0]

        root = self.parse_xml(self.xml_path('Training Level Record'))
        
        for child in root:
            obj, created = models.TrainingLevelQualification.objects.update_or_create(
                pk = int(child.find('ID').text),
                trainee = int(child.find('Member_x0020_ID').text),
                level = int(child.find('Training_x0020_Level_x0020_ID').text),
                confirmed_on = child.find('Date_x0020_Level_x0020_Awarded').text
                #confirmed by?
            )
        
            if created:
                tally[1] += 1
            else:
                tally[0] += 1
        
        print('TrainingLevelQualifications - Updated: {}, Created: {}'.format(tally[0], tally[1]))



















































    

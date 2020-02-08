import os
import datetime
import xml.etree.ElementTree as ET
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Imports old db from XML dump'

    epoch = datetime.date(1970, 1, 1)

    def handle(self, *args, **options):
        # self.update_statuses()
        # self.update_suppliers()
        self.update_cable_statuses()

    @staticmethod
    def xml_path(file):
        return os.path.join(settings.BASE_DIR, 'data/DB_Dump/{}'.format(file))

    @staticmethod
    def parse_xml(file):
        tree = ET.parse(file)

        return tree.getroot()

    def update_statuses(self):
        file = self.xml_path('TEC_Assets.xml')
        tree = ET.parse(file)
        root = tree.getroot()

        # map old status pk to new status pk
        status_map = {
            2: 2,
            3: 4,
            4: 3,
            5: 5,
            6: 1
        }

        for child in root:
            status = int(child.find('StatusID').text)
            child.find('StatusID').text = str(status_map[status])

        tree.write(file)

    def update_suppliers(self):
        old_file = self.xml_path('TEC_Asset_Suppliers.xml')
        old_tree = ET.parse(old_file)
        old_root = old_tree.getroot()

        new_file = self.xml_path('TEC_Asset_Suppliers_new.xml')
        new_tree = ET.parse(new_file)
        new_root = new_tree.getroot()

        # map old supplier pk to new supplier pk
        supplier_map = dict()

        def find_in_old(name, root):
            for child in root:
                found_id = child.find('Supplier_x0020_Id').text
                found_name = child.find('Supplier_x0020_Name').text

                if found_name == name:
                    return found_id

        for new_child in new_root:
            new_id = new_child.find('Supplier_x0020_Id').text
            new_name = new_child.find('Supplier_x0020_Name').text

            old_id = find_in_old(new_name, old_root)

            supplier_map[int(old_id)] = int(new_id)

        file = self.xml_path('TEC_Assets.xml')
        tree = ET.parse(file)
        root = tree.getroot()

        for child in root:
            try:
                supplier = int(child.find('Supplier_x0020_Id').text)
                child.find('Supplier_x0020_Id').text = str(supplier_map[supplier])
            except AttributeError:
                pass

        tree.write(file)

    def update_cable_statuses(self):
        file = self.xml_path('TEC_Cables.xml')
        tree = ET.parse(file)
        root = tree.getroot()

        # map old status pk to new status pk
        status_map = {
            0: 7,
            1: 3,
            3: 2,
            4: 5,
            6: 6,
            7: 1,
            8: 4,
            9: 2,
        }

        for child in root:
            status = int(child.find('Status').text)
            child.find('Status').text = str(status_map[status])

        tree.write(file)

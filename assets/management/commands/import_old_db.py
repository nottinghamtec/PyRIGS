import os
import datetime
import xml.etree.ElementTree as ET
from django.core.management.base import BaseCommand
from django.conf import settings

from assets import models


class Command(BaseCommand):
    help = 'Imports old db from XML dump'

    epoch = datetime.date(1970, 1, 1)

    def handle(self, *args, **options):
        self.import_categories()
        self.import_statuses()
        self.import_suppliers()
        self.import_collections()
        self.import_assets()
        self.import_cables()

    @staticmethod
    def xml_path(file):
        return os.path.join(settings.BASE_DIR, 'data/DB_Dump/{}'.format(file))

    @staticmethod
    def parse_xml(file):
        tree = ET.parse(file)

        return tree.getroot()

    def import_categories(self):
        # 0: updated, 1: created
        tally = [0, 0]
        root = self.parse_xml(self.xml_path('TEC_Asset_Categories.xml'))

        for child in root:
            obj, created = models.AssetCategory.objects.update_or_create(
                pk=int(child.find('AssetCategoryID').text),
                name=child.find('AssetCategory').text
            )

            if created:
                tally[1] += 1
            else:
                tally[0] += 1

        print('Categories - Updated: {}, Created: {}'.format(tally[0], tally[1]))

    def import_statuses(self):
        # 0: updated, 1: created
        tally = [0, 0]
        root = self.parse_xml(self.xml_path('TEC_Asset_Status_new.xml'))

        for child in root:
            obj, created = models.AssetStatus.objects.update_or_create(
                pk=int(child.find('StatusID').text),
                name=child.find('Status').text
            )

            if created:
                tally[1] += 1
            else:
                tally[0] += 1

        print('Statuses - Updated: {}, Created: {}'.format(tally[0], tally[1]))

    def import_suppliers(self):
        # 0: updated, 1: created
        tally = [0, 0]
        root = self.parse_xml(self.xml_path('TEC_Asset_Suppliers_new.xml'))

        for child in root:
            obj, created = models.Supplier.objects.update_or_create(
                pk=int(child.find('Supplier_x0020_Id').text),
                name=child.find('Supplier_x0020_Name').text
            )

            if created:
                tally[1] += 1
            else:
                tally[0] += 1

        print('Suppliers - Updated: {}, Created: {}'.format(tally[0], tally[1]))

    def import_assets(self):
        # 0: updated, 1: created
        tally = [0, 0]
        root = self.parse_xml(self.xml_path('TEC_Assets.xml'))

        for child in root:
            defaults = dict()

            # defaults['pk'] = int(child.find('ID').text)
            defaults['asset_id'] = child.find('AssetID').text

            try:
                defaults['description'] = child.find('AssetDescription').text
            except AttributeError:
                defaults['description'] = 'None'

            defaults['category'] = models.AssetCategory.objects.get(pk=int(child.find('AssetCategoryID').text))
            defaults['status'] = models.AssetStatus.objects.get(pk=int(child.find('StatusID').text))

            try:
                defaults['serial_number'] = child.find('SerialNumber').text
            except AttributeError:
                pass

            try:
                defaults['purchased_from'] = models.Supplier.objects.get(pk=int(child.find('Supplier_x0020_Id').text))
            except AttributeError:
                pass

            try:
                defaults['date_acquired'] = datetime.datetime.strptime(child.find('DateAcquired').text, '%d/%m/%Y').date()
            except AttributeError:
                defaults['date_acquired'] = self.epoch

            try:
                defaults['date_sold'] = datetime.datetime.strptime(child.find('DateSold').text, '%d/%m/%Y').date()
            except AttributeError:
                pass

            try:
                defaults['purchase_price'] = float(child.find('Replacement_x0020_Value').text)
            except AttributeError:
                pass

            try:
                defaults['salvage_value'] = float(child.find('SalvageValue').text)
            except AttributeError:
                pass

            try:
                defaults['comments'] = child.find('Comments').text
            except AttributeError:
                pass

            try:
                date = child.find('NextSchedMaint').text.split('T')[0]
                defaults['next_sched_maint'] = datetime.datetime.strptime(date, '%Y-%m-%d').date()
            except AttributeError:
                pass

            print(defaults)

            obj, created = models.Asset.objects.update_or_create(**defaults)

            if created:
                tally[1] += 1
            else:
                tally[0] += 1

        print('Assets - Updated: {}, Created: {}'.format(tally[0], tally[1]))

    def import_collections(self):
        tally = [0, 0]
        root = self.parse_xml(self.xml_path('TEC_Cable_Collections.xml'))

        for child in root:
            defaults = dict()

            defaults['pk'] = int(child.find('ID').text)
            defaults['name'] = child.find('Cable_x0020_Trunk').text

            obj, created = models.Collection.objects.update_or_create(**defaults)

            if created:
                tally[1] += 1
            else:
                tally[0] += 1

        print('Collections - Updated: {}, Created: {}'.format(tally[0], tally[1]))

    def import_cables(self):
        tally = [0, 0]
        root = self.parse_xml(self.xml_path('TEC_Cables.xml'))

        for child in root:
            defaults = dict()

            defaults['asset_id'] = child.find('Asset_x0020_Number').text

            try:
                defaults['description'] = child.find('Type_x0020_of_x0020_Cable').text
            except AttributeError:
                defaults['description'] = 'None'

            defaults['is_cable'] = True
            defaults['category'] = models.AssetCategory.objects.get(pk=9)

            try:
                defaults['length'] = child.find('Length_x0020__x0028_m_x0029_').text
            except AttributeError:
                pass

            defaults['status'] = models.AssetStatus.objects.get(pk=int(child.find('Status').text))

            try:
                defaults['comments'] = child.find('Comments').text
            except AttributeError:
                pass

            try:
                collection_id = int(child.find('Collection').text)
                if collection_id != 0:
                    defaults['collection'] = models.Collection.objects.get(pk=collection_id)
            except AttributeError:
                pass

            try:
                defaults['purchase_price'] = float(child.find('Purchase_x0020_Price').text)
            except AttributeError:
                pass

            defaults['date_acquired'] = self.epoch

            print(defaults)

            obj, created = models.Asset.objects.update_or_create(**defaults)

            if created:
                tally[1] += 1
            else:
                tally[0] += 1

        print('Collections - Updated: {}, Created: {}'.format(tally[0], tally[1]))

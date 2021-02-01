import random

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from reversion import revisions as reversion

from RIGS import models as rigsmodels
from assets import models


class Command(BaseCommand):
    help = 'Creates some sample data for testing'

    categories = []
    statuses = []
    suppliers = []
    connectors = []
    cable_types = []
    assets = []

    def handle(self, *args, **kwargs):
        from django.conf import settings

        if not (settings.DEBUG or settings.STAGING):
            raise CommandError('You cannot run this command in production')

        random.seed('Some object to see the random number generator')

        self.create_categories()
        models.AssetCategory.objects.bulk_create(self.categories)
        self.create_statuses()
        models.AssetStatus.objects.bulk_create(self.statuses)
        self.create_suppliers()
        models.Supplier.objects.bulk_create(self.suppliers)
        self.create_assets()
        self.create_connectors()
        models.Connector.objects.bulk_create(self.connectors)
        self.create_cable_types()
        models.CableType.objects.bulk_create(self.cable_types)
        self.create_cables()
        models.Asset.objects.bulk_create(self.assets)

    def create_statuses(self):
        choices = [('In Service', True, 'success'), ('Lost', False, 'warning'), ('Binned', False, 'danger'), ('Sold', False, 'danger'), ('Broken', False, 'warning')]
        pk = 1
        for stat in choices:
            self.statuses.append(models.AssetStatus(pk=pk, name=stat[0], should_show=stat[1], display_class=stat[2]))
            pk += 1

    def create_suppliers(self):
        choices = ["Acme, inc.", "Widget Corp", "123 Warehousing", "Demo Company", "Smith and Co.", "Foo Bars", "ABC Telecom", "Fake Brothers", "QWERTY Logistics", "Demo, inc.", "Sample Company", "Sample, inc", "Acme Corp", "Allied Biscuit", "Ankh-Sto Associates", "Extensive Enterprise", "Galaxy Corp", "Globo-Chem", "Mr. Sparkle", "Globex Corporation", "LexCorp", "LuthorCorp", "North Central Positronics", "Omni Consimer Products", "Praxis Corporation", "Sombra Corporation", "Sto Plains Holdings", "Tessier-Ashpool", "Wayne Enterprises", "Wentworth Industries", "ZiffCorp", "Bluth Company", "Strickland Propane", "Thatherton Fuels", "Three Waters", "Water and Power", "Western Gas & Electric", "Mammoth Pictures", "Mooby Corp", "Gringotts", "Thrift Bank", "Flowers By Irene", "The Legitimate Businessmens Club", "Osato Chemicals", "Transworld Consortium", "Universal Export", "United Fried Chicken", "Virtucon", "Kumatsu Motors", "Keedsler Motors", "Powell Motors", "Industrial Automation", "Sirius Cybernetics Corporation", "U.S. Robotics and Mechanical Men", "Colonial Movers", "Corellian Engineering Corporation", "Incom Corporation", "General Products", "Leeding Engines Ltd.", "Blammo",  # noqa
                     "Input, Inc.", "Mainway Toys", "Videlectrix", "Zevo Toys", "Ajax", "Axis Chemical Co.", "Barrytron", "Carrys Candles", "Cogswell Cogs", "Spacely Sprockets", "General Forge and Foundry", "Duff Brewing Company", "Dunder Mifflin", "General Services Corporation", "Monarch Playing Card Co.", "Krustyco", "Initech", "Roboto Industries", "Primatech", "Sonky Rubber Goods", "St. Anky Beer", "Stay Puft Corporation", "Vandelay Industries", "Wernham Hogg", "Gadgetron", "Burleigh and Stronginthearm", "BLAND Corporation", "Nordyne Defense Dynamics", "Petrox Oil Company", "Roxxon", "McMahon and Tate", "Sixty Second Avenue", "Charles Townsend Agency", "Spade and Archer", "Megadodo Publications", "Rouster and Sideways", "C.H. Lavatory and Sons", "Globo Gym American Corp", "The New Firm", "SpringShield", "Compuglobalhypermeganet", "Data Systems", "Gizmonic Institute", "Initrode", "Taggart Transcontinental", "Atlantic Northern", "Niagular", "Plow King", "Big Kahuna Burger", "Big T Burgers and Fries", "Chez Quis", "Chotchkies", "The Frying Dutchman", "Klimpys", "The Krusty Krab", "Monks Diner", "Milliways", "Minuteman Cafe", "Taco Grande", "Tip Top Cafe", "Moes Tavern", "Central Perk", "Chasers"]  # noqa
        pk = 1
        for supplier in choices:
            self.suppliers.append(models.Supplier(pk=pk, name=supplier))
            pk += 1

    def create_categories(self):
        choices = ['Case', 'Video', 'General', 'Sound', 'Lighting', 'Rigging']
        pk = 1
        for cat in choices:
            self.categories.append(models.AssetCategory(pk=pk, name=cat))
            pk += 1

    def create_assets(self):
        asset_description = ['Large cable', 'Shiny thing', 'New lights', 'Really expensive microphone', 'Box of fuse flaps', 'Expensive tool we didn\'t agree to buy', 'Cable drums', 'Boring amount of tape', 'Video stuff no one knows how to use', 'More amplifiers', 'Heatshrink']
        pk = 1
        for i in range(100):
            asset = models.Asset(
                pk=pk,
                asset_id=str(pk),
                description=random.choice(asset_description),
                category=random.choice(self.categories),
                status=random.choice(self.statuses),
                date_acquired=timezone.now().date()
            )

            if i % 4 == 0 and self.assets:
                asset.parent = random.choice(self.assets)

            if i % 3 == 0:
                asset.purchased_from = random.choice(self.suppliers)
            self.assets.append(asset)
            pk += 1

    def create_cables(self):
        asset_description = ['The worm', 'Harting without a cap', 'Heavy cable', 'Extension lead', 'IEC cable that we should remember to prep']
        asset_prefixes = ["C", "C4P", "CBNC", "CDMX", "CDV", "CRCD", "CSOCA", "CXLR"]

        csas = [0.75, 1.00, 1.25, 2.5, 4]
        lengths = [1, 2, 5, 10, 15, 20, 25, 30, 50, 100]
        pk = 102  # Offset to avoid other asset IDs
        for i in range(100):
            asset = models.Asset(
                pk=pk,
                asset_id=random.choice(asset_prefixes) + str(pk),
                description=random.choice(asset_description),
                category=random.choice(self.categories),
                status=random.choice(self.statuses),
                date_acquired=timezone.now().date(),

                is_cable=True,
                cable_type=random.choice(self.cable_types),
                csa=random.choice(csas),
                length=random.choice(lengths),
            )

            if i % 4 == 0 and self.assets:
                asset.parent = random.choice(self.assets)

            if i % 3 == 0:
                asset.purchased_from = random.choice(self.suppliers)
            self.assets.append(asset)
            pk += 1

    def create_connectors(self):
        connectors = [
            {"description": "13A UK", "current_rating": 13, "voltage_rating": 230, "num_pins": 3},
            {"description": "16A", "current_rating": 16, "voltage_rating": 230, "num_pins": 3},
            {"description": "32/3", "current_rating": 32, "voltage_rating": 400, "num_pins": 5},
            {"description": "Socapex", "current_rating": 23, "voltage_rating": 600, "num_pins": 19},
        ]
        pk = 1
        for connector in connectors:
            self.connectors.append(models.Connector(pk=pk, **connector))
            pk += 1

    def create_cable_types(self):
        cores = [3, 5]
        circuits = [1, 2, 3, 6]
        pk = 1
        for i in range(10):
            self.cable_types.append(models.CableType(pk=pk, plug=random.choice(self.connectors), socket=random.choice(self.connectors), circuits=random.choice(circuits), cores=random.choice(cores)))
            pk += 1

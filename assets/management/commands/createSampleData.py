from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.utils import timezone
import random

from assets import models


class Command(BaseCommand):
    help = 'Creates some sample data for testing'

    def handle(self, *args, **kwargs):
        from django.conf import settings

        if not settings.DEBUG:
            raise CommandError('You cannot run this command in production')

        random.seed('Some object to see the random number generator')

        call_command('createBaseUsers')

        self.create_categories()
        self.create_statuses()
        self.create_suppliers()
        self.create_assets()

    def create_categories(self):
        categories = ['Case', 'Video', 'General', 'Sound', 'Lighting', 'Rigging']

        for cat in categories:
            models.AssetCategory.objects.create(name=cat)

    def create_statuses(self):
        statuses = ['In Service', 'Lost', 'Binned', 'Sold', 'Broken']

        for stat in statuses:
            models.AssetStatus.objects.create(name=stat)

    def create_suppliers(self):
        suppliers = ["Acme, inc.","Widget Corp","123 Warehousing","Demo Company","Smith and Co.","Foo Bars","ABC Telecom","Fake Brothers","QWERTY Logistics","Demo, inc.","Sample Company","Sample, inc","Acme Corp","Allied Biscuit","Ankh-Sto Associates","Extensive Enterprise","Galaxy Corp","Globo-Chem","Mr. Sparkle","Globex Corporation","LexCorp","LuthorCorp","North Central Positronics","Omni Consimer Products","Praxis Corporation","Sombra Corporation","Sto Plains Holdings","Tessier-Ashpool","Wayne Enterprises","Wentworth Industries","ZiffCorp","Bluth Company","Strickland Propane","Thatherton Fuels","Three Waters","Water and Power","Western Gas & Electric","Mammoth Pictures","Mooby Corp","Gringotts","Thrift Bank","Flowers By Irene","The Legitimate Businessmens Club","Osato Chemicals","Transworld Consortium","Universal Export","United Fried Chicken","Virtucon","Kumatsu Motors","Keedsler Motors","Powell Motors","Industrial Automation","Sirius Cybernetics Corporation","U.S. Robotics and Mechanical Men","Colonial Movers","Corellian Engineering Corporation","Incom Corporation","General Products","Leeding Engines Ltd.","Blammo","Input, Inc.","Mainway Toys","Videlectrix","Zevo Toys","Ajax","Axis Chemical Co.","Barrytron","Carrys Candles","Cogswell Cogs","Spacely Sprockets","General Forge and Foundry","Duff Brewing Company","Dunder Mifflin","General Services Corporation","Monarch Playing Card Co.","Krustyco","Initech","Roboto Industries","Primatech","Sonky Rubber Goods","St. Anky Beer","Stay Puft Corporation","Vandelay Industries","Wernham Hogg","Gadgetron","Burleigh and Stronginthearm","BLAND Corporation","Nordyne Defense Dynamics","Petrox Oil Company","Roxxon","McMahon and Tate","Sixty Second Avenue","Charles Townsend Agency","Spade and Archer","Megadodo Publications","Rouster and Sideways","C.H. Lavatory and Sons","Globo Gym American Corp","The New Firm","SpringShield","Compuglobalhypermeganet","Data Systems","Gizmonic Institute","Initrode","Taggart Transcontinental","Atlantic Northern","Niagular","Plow King","Big Kahuna Burger","Big T Burgers and Fries","Chez Quis","Chotchkies","The Frying Dutchman","Klimpys","The Krusty Krab","Monks Diner","Milliways","Minuteman Cafe","Taco Grande","Tip Top Cafe","Moes Tavern","Central Perk","Chasers"]

        for supplier in suppliers:
            models.Supplier.objects.create(name=supplier)

    def create_assets(self):
        assest_description = ['Large cable', 'Shiny thing', 'New lights', 'Really expensive microphone', 'Box of fuse flaps', 'Expensive tool we didn\'t agree to buy', 'Cable drums', 'Boring amount of tape', 'Video stuff no one knows how to use', 'More amplifiers', 'Heatshrink']

        categories = models.AssetCategory.objects.all()
        statuses = models.AssetStatus.objects.all()
        suppliers = models.Supplier.objects.all()

        for i in range(100):
            asset = models.Asset.objects.create(
                asset_id='{}'.format(i),
                description=random.choice(assest_description),
                category=random.choice(categories),
                status=random.choice(statuses),
                date_acquired=timezone.now().date(),
            )

            if i % 3 == 0:
                asset.purchased_from = random.choice(suppliers)

            asset.save()

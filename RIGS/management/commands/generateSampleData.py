from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import Group, Permission

from RIGS import models
class Command(BaseCommand):
    help = 'Adds sample data to use for testing'
    can_import_settings = True

    people = []
    organisations = []
    venues = []
    profiles = []

    keyholder_group = None
    finance_group = None


    def handle(self, *args, **options):
        from django.conf import settings

        if not (settings.DEBUG or settings.STAGING):
            raise CommandError('You cannot run this command in production')



        profile = models.Profile.objects.create(username="testuser", email="1@test.com", is_superuser=True,
                                                    is_active=True, is_staff=True)
        profile.set_password('testuser')
        profile.save()
        

        models.VatRate.objects.create(start_at='2014-03-05',rate=0.20,comment='test1')

        self.setupPeople()
        self.setupOrganisations()
        self.setupVenues()
        self.setupGroups()
        self.setupProfiles()

    def setupPeople(self):
        names = ["Regulus Black","Sirius Black","Lavender Brown","Cho Chang","Vincent Crabbe Sr","Vincent Crabbe","Bartemius Crouch Jr","Fleur Delacour","Cedric Diggory","Alberforth Dumbledore","Albus Dumbledore","Dudley Dursley","Petunia Dursley","Vernon Dursley","Argus Filch","Seamus Finnigan","Nicolas Flamel","Cornelius Fudge","Goyle Sr.","Gregory Goyle","Hermione Granger","Rubeus Hagrid","Igor Karkaroff","Viktor Krum","Bellatrix Lestrange","Alice Longbottom","Frank Longbottom","Neville Longbottom","Luna Lovegood","Xenophilius Lovegood","Remus Lupin","Draco Malfoy","Lucius Malfoy","Narcissa Malfoy","Olympe Maxime","Minerva McGonagall","Mad-Eye Moody","Peter Pettigrew","Harry Potter","James Potter","Lily Potter","Quirinus Quirrell","Tom Riddle Sr.","Mary Riddle","Lord Voldemort","Rita Skeeter","Severus Snape","Nymphadora Tonks","Dolores Janes Umbridge","Arthur Weasley","Bill Weasley","Charlie Weasley","Fred Weasley","George Weasley","Ginny Weasley","Molly Weasley","Percy Weasley","Ron Weasley","Dobby","Fluffy","Hedwig","Moaning Myrtle","Aragog","Grawp"]
        for i, name in enumerate(names):
            newPerson = models.Person.objects.create(name=name)
            if i % 3 == 0:
                newPerson.email = "address@person.com"

            if i % 5 == 0:
                newPerson.notes = "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua"

            if i % 7 == 0:
                newPerson.address = "1 Person Test Street \n Demoton \n United States of TEC \n RMRF 567"

            if i % 9 == 0:
                newPerson.phone = "01234 567894"

            newPerson.save()
            self.people.append(newPerson)

    def setupOrganisations(self):
        names = ["Acme, inc.","Widget Corp","123 Warehousing","Demo Company","Smith and Co.","Foo Bars","ABC Telecom","Fake Brothers","QWERTY Logistics","Demo, inc.","Sample Company","Sample, inc","Acme Corp","Allied Biscuit","Ankh-Sto Associates","Extensive Enterprise","Galaxy Corp","Globo-Chem","Mr. Sparkle","Globex Corporation","LexCorp","LuthorCorp","North Central Positronics","Omni Consimer Products","Praxis Corporation","Sombra Corporation","Sto Plains Holdings","Tessier-Ashpool","Wayne Enterprises","Wentworth Industries","ZiffCorp","Bluth Company","Strickland Propane","Thatherton Fuels","Three Waters","Water and Power","Western Gas & Electric","Mammoth Pictures","Mooby Corp","Gringotts","Thrift Bank","Flowers By Irene","The Legitimate Businessmens Club","Osato Chemicals","Transworld Consortium","Universal Export","United Fried Chicken","Virtucon","Kumatsu Motors","Keedsler Motors","Powell Motors","Industrial Automation","Sirius Cybernetics Corporation","U.S. Robotics and Mechanical Men","Colonial Movers","Corellian Engineering Corporation","Incom Corporation","General Products","Leeding Engines Ltd.","Blammo","Input, Inc.","Mainway Toys","Videlectrix","Zevo Toys","Ajax","Axis Chemical Co.","Barrytron","Carrys Candles","Cogswell Cogs","Spacely Sprockets","General Forge and Foundry","Duff Brewing Company","Dunder Mifflin","General Services Corporation","Monarch Playing Card Co.","Krustyco","Initech","Roboto Industries","Primatech","Sonky Rubber Goods","St. Anky Beer","Stay Puft Corporation","Vandelay Industries","Wernham Hogg","Gadgetron","Burleigh and Stronginthearm","BLAND Corporation","Nordyne Defense Dynamics","Petrox Oil Company","Roxxon","McMahon and Tate","Sixty Second Avenue","Charles Townsend Agency","Spade and Archer","Megadodo Publications","Rouster and Sideways","C.H. Lavatory and Sons","Globo Gym American Corp","The New Firm","SpringShield","Compuglobalhypermeganet","Data Systems","Gizmonic Institute","Initrode","Taggart Transcontinental","Atlantic Northern","Niagular","Plow King","Big Kahuna Burger","Big T Burgers and Fries","Chez Quis","Chotchkies","The Frying Dutchman","Klimpys","The Krusty Krab","Monks Diner","Milliways","Minuteman Cafe","Taco Grande","Tip Top Cafe","Moes Tavern","Central Perk","Chasers"]
        for i, name in enumerate(names):
            newOrganisation = models.Organisation.objects.create(name=name)
            if i % 2 == 0:
                newOrganisation.has_su_account = True

            if i % 3 == 0:
                newOrganisation.email = "address@organisation.com"

            if i % 5 == 0:
                newOrganisation.notes = "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua"

            if i % 7 == 0:
                newOrganisation.address = "1 Organisation Test Street \n Demoton \n United States of TEC \n RMRF 567"

            if i % 9 == 0:
                newOrganisation.phone = "01234 567894"

            newOrganisation.save()
            self.organisations.append(newOrganisation)

    def setupVenues(self):
        names = ["Bear Island","Crossroads Inn","Deepwood Motte","The Dreadfort","The Eyrie","Greywater Watch","The Iron Islands","Karhold","Moat Cailin","Oldstones","Raventree Hall","Riverlands","The Ruby Ford","Saltpans","Seagard","Torrhen's Square","The Trident","The Twins","The Vale of Arryn","The Whispering Wood","White Harbor","Winterfell","The Arbor","Ashemark","Brightwater Keep","Casterly Rock","Clegane's Keep","Dragonstone","Dorne","God's Eye","The Golden Tooth","Harrenhal","Highgarden","Horn Hill","Fingers","King's Landing","Lannisport","Oldtown","Rainswood","Storm's End","Summerhall","Sunspear","Tarth","Castle Black","Craster's Keep","Fist of the First Men","The Frostfangs","The Gift","The Skirling Pass","The Wall","Asshai","Astapor","Braavos","The Dothraki Sea","Lys","Meereen","Myr","Norvos","Pentos","Qarth","Qohor","The Red Waste","Tyrosh","Vaes Dothrak","Valyria","Village of the Lhazareen","Volantis","Yunkai"]
        for i, name in enumerate(names):
            newVenue = models.Venue.objects.create(name=name)
            if i % 2 == 0:
                newVenue.three_phase_available = True

            if i % 3 == 0:
                newVenue.email = "address@venue.com"

            if i % 5 == 0:
                newVenue.notes = "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua"

            if i % 7 == 0:
                newVenue.address = "1 Venue Test Street \n Demoton \n United States of TEC \n RMRF 567"

            if i % 9 == 0:
                newVenue.phone = "01234 567894"

            newVenue.save()
            self.venues.append(newVenue)

    def setupGroups(self):
        self.keyholder_group = Group.objects.create(name='Keyholders')
        self.finance_group = Group.objects.create(name='Finance')

        keyholderPerms = ["add_event","change_event","view_event","add_eventitem","change_eventitem","delete_eventitem","add_organisation","change_organisation","view_organisation","add_person","change_person","view_person","view_profile","add_venue","change_venue","view_venue"]
        financePerms = ["change_event","view_event","add_eventitem","change_eventitem","add_invoice","change_invoice","view_invoice","add_organisation","change_organisation","view_organisation","add_payment","change_payment","delete_payment","add_person","change_person","view_person"]

        for permId in keyholderPerms:
            self.keyholder_group.permissions.add(Permission.objects.get(codename=permId))

        for permId in financePerms:
            self.finance_group.permissions.add(Permission.objects.get(codename=permId))

    def setupProfiles(self):
        names = ["Clara Oswin Oswald","Rory Williams","Amy Pond","River Song","Martha Jones","Donna Noble","Jack Harkness","Mickey Smith","Rose Tyler"]
        for i, name in enumerate(names):
            newProfile = models.Profile.objects.create(username=name.replace(" ",""), first_name=name.split(" ")[0], last_name=name.split(" ")[-1],
                                                         email=name.replace(" ","")+"@example.com",
                                                        initials="".join([ j[0].upper() for j in name.split() ]))
            if i % 2 == 0:
                newProfile.phone = "01234 567894"

            newProfile.save()
            self.profiles.append(newProfile)

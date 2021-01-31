import datetime
import random

from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from reversion import revisions as reversion

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
    hs_group = None

    def handle(self, *args, **options):
        from django.conf import settings

        if not (settings.DEBUG or settings.STAGING):
            raise CommandError('You cannot run this command in production')

        random.seed(
            'Some object to seed the random number generator')  # otherwise it is done by time, which could lead to inconsistant tests

        with transaction.atomic():
            models.VatRate.objects.create(start_at='2014-03-05', rate=0.20, comment='test1')

            self.setupGenericProfiles()

            self.setupPeople()
            self.setupOrganisations()
            self.setupVenues()

            self.setupGroups()

            self.setupEvents()

            self.setupUsefulProfiles()

    def setupPeople(self):
        names = ["Regulus Black", "Sirius Black", "Lavender Brown", "Cho Chang", "Vincent Crabbe", "Vincent Crabbe",
                 "Bartemius Crouch", "Fleur Delacour", "Cedric Diggory", "Alberforth Dumbledore", "Albus Dumbledore",
                 "Dudley Dursley", "Petunia Dursley", "Vernon Dursley", "Argus Filch", "Seamus Finnigan",
                 "Nicolas Flamel", "Cornelius Fudge", "Goyle", "Gregory Goyle", "Hermione Granger", "Rubeus Hagrid",
                 "Igor Karkaroff", "Viktor Krum", "Bellatrix Lestrange", "Alice Longbottom", "Frank Longbottom",
                 "Neville Longbottom", "Luna Lovegood", "Xenophilius Lovegood",  # noqa
                 "Remus Lupin", "Draco Malfoy", "Lucius Malfoy", "Narcissa Malfoy", "Olympe Maxime",
                 "Minerva McGonagall", "Mad-Eye Moody", "Peter Pettigrew", "Harry Potter", "James Potter",
                 "Lily Potter", "Quirinus Quirrell", "Tom Riddle", "Mary Riddle", "Lord Voldemort", "Rita Skeeter",
                 "Severus Snape", "Nymphadora Tonks", "Dolores Janes Umbridge", "Arthur Weasley", "Bill Weasley",
                 "Charlie Weasley", "Fred Weasley", "George Weasley", "Ginny Weasley", "Molly Weasley", "Percy Weasley",
                 "Ron Weasley", "Dobby", "Fluffy", "Hedwig", "Moaning Myrtle", "Aragog", "Grawp"]  # noqa
        for i, name in enumerate(names):
            with reversion.create_revision():
                reversion.set_user(random.choice(self.profiles))

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
        names = ["Acme, inc.", "Widget Corp", "123 Warehousing", "Demo Company", "Smith and Co.", "Foo Bars",
                 "ABC Telecom", "Fake Brothers", "QWERTY Logistics", "Demo, inc.", "Sample Company", "Sample, inc",
                 "Acme Corp", "Allied Biscuit", "Ankh-Sto Associates", "Extensive Enterprise", "Galaxy Corp",
                 "Globo-Chem", "Mr. Sparkle", "Globex Corporation", "LexCorp", "LuthorCorp",
                 "North Central Positronics", "Omni Consimer Products", "Praxis Corporation", "Sombra Corporation",
                 "Sto Plains Holdings", "Tessier-Ashpool", "Wayne Enterprises", "Wentworth Industries", "ZiffCorp",
                 "Bluth Company", "Strickland Propane", "Thatherton Fuels", "Three Waters", "Water and Power",
                 "Western Gas & Electric", "Mammoth Pictures", "Mooby Corp", "Gringotts", "Thrift Bank",
                 "Flowers By Irene", "The Legitimate Businessmens Club", "Osato Chemicals", "Transworld Consortium",
                 "Universal Export", "United Fried Chicken", "Virtucon", "Kumatsu Motors", "Keedsler Motors",
                 "Powell Motors", "Industrial Automation", "Sirius Cybernetics Corporation",
                 "U.S. Robotics and Mechanical Men", "Colonial Movers", "Corellian Engineering Corporation",
                 "Incom Corporation", "General Products", "Leeding Engines Ltd.", "Blammo",  # noqa
                 "Input, Inc.", "Mainway Toys", "Videlectrix", "Zevo Toys", "Ajax", "Axis Chemical Co.", "Barrytron",
                 "Carrys Candles", "Cogswell Cogs", "Spacely Sprockets", "General Forge and Foundry",
                 "Duff Brewing Company", "Dunder Mifflin", "General Services Corporation", "Monarch Playing Card Co.",
                 "Krustyco", "Initech", "Roboto Industries", "Primatech", "Sonky Rubber Goods", "St. Anky Beer",
                 "Stay Puft Corporation", "Vandelay Industries", "Wernham Hogg", "Gadgetron",
                 "Burleigh and Stronginthearm", "BLAND Corporation", "Nordyne Defense Dynamics", "Petrox Oil Company",
                 "Roxxon", "McMahon and Tate", "Sixty Second Avenue", "Charles Townsend Agency", "Spade and Archer",
                 "Megadodo Publications", "Rouster and Sideways", "C.H. Lavatory and Sons", "Globo Gym American Corp",
                 "The New Firm", "SpringShield", "Compuglobalhypermeganet", "Data Systems", "Gizmonic Institute",
                 "Initrode", "Taggart Transcontinental", "Atlantic Northern", "Niagular", "Plow King",
                 "Big Kahuna Burger", "Big T Burgers and Fries", "Chez Quis", "Chotchkies", "The Frying Dutchman",
                 "Klimpys", "The Krusty Krab", "Monks Diner", "Milliways", "Minuteman Cafe", "Taco Grande",
                 "Tip Top Cafe", "Moes Tavern", "Central Perk", "Chasers"]  # noqa
        for i, name in enumerate(names):
            with reversion.create_revision():
                reversion.set_user(random.choice(self.profiles))
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
        names = ["Bear Island", "Crossroads Inn", "Deepwood Motte", "The Dreadfort", "The Eyrie", "Greywater Watch",
                 "The Iron Islands", "Karhold", "Moat Cailin", "Oldstones", "Raventree Hall", "Riverlands",
                 "The Ruby Ford", "Saltpans", "Seagard", "Torrhen's Square", "The Trident", "The Twins",
                 "The Vale of Arryn", "The Whispering Wood", "White Harbor", "Winterfell", "The Arbor", "Ashemark",
                 "Brightwater Keep", "Casterly Rock", "Clegane's Keep", "Dragonstone", "Dorne", "God's Eye",
                 "The Golden Tooth",  # noqa
                 "Harrenhal", "Highgarden", "Horn Hill", "Fingers", "King's Landing", "Lannisport", "Oldtown",
                 "Rainswood", "Storm's End", "Summerhall", "Sunspear", "Tarth", "Castle Black", "Craster's Keep",
                 "Fist of the First Men", "The Frostfangs", "The Gift", "The Skirling Pass", "The Wall", "Asshai",
                 "Astapor", "Braavos", "The Dothraki Sea", "Lys", "Meereen", "Myr", "Norvos", "Pentos", "Qarth",
                 "Qohor", "The Red Waste", "Tyrosh", "Vaes Dothrak", "Valyria", "Village of the Lhazareen", "Volantis",
                 "Yunkai"]  # noqa
        for i, name in enumerate(names):
            with reversion.create_revision():
                reversion.set_user(random.choice(self.profiles))
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
        self.hs_group = Group.objects.create(name='H&S')

        keyholderPerms = ["add_event", "change_event", "view_event",
                          "add_eventitem", "change_eventitem", "delete_eventitem",
                          "add_organisation", "change_organisation", "view_organisation",
                          "add_person", "change_person", "view_person", "view_profile",
                          "add_venue", "change_venue", "view_venue",
                          "add_asset", "change_asset", "delete_asset",
                          "view_asset", "view_supplier", "change_supplier", "asset_finance",
                          "add_supplier", "view_cabletype", "change_cabletype",
                          "add_cabletype", "view_eventchecklist", "change_eventchecklist",
                          "add_eventchecklist", "view_riskassessment", "change_riskassessment",
                          "add_riskassessment", "add_eventchecklistcrew", "change_eventchecklistcrew",
                          "delete_eventchecklistcrew", "view_eventchecklistcrew", "add_eventchecklistvehicle",
                          "change_eventchecklistvehicle",
                          "delete_eventchecklistvehicle", "view_eventchecklistvehicle", ]
        financePerms = keyholderPerms + ["add_invoice", "change_invoice", "view_invoice",
                                         "add_payment", "change_payment", "delete_payment"]
        hsPerms = keyholderPerms + ["review_riskassessment", "review_eventchecklist"]

        for permId in keyholderPerms:
            self.keyholder_group.permissions.add(Permission.objects.get(codename=permId))

        for permId in financePerms:
            self.finance_group.permissions.add(Permission.objects.get(codename=permId))

        for permId in hsPerms:
            self.hs_group.permissions.add(Permission.objects.get(codename=permId))

    def setupGenericProfiles(self):
        names = ["Clara Oswin Oswald", "Rory Williams", "Amy Pond", "River Song", "Martha Jones", "Donna Noble",
                 "Jack Harkness", "Mickey Smith", "Rose Tyler"]
        for i, name in enumerate(names):
            newProfile = models.Profile.objects.create(username=name.replace(" ", ""), first_name=name.split(" ")[0],
                                                       last_name=name.split(" ")[-1],
                                                       email=name.replace(" ", "") + "@example.com",
                                                       initials="".join([j[0].upper() for j in name.split()]))
            if i % 2 == 0:
                newProfile.phone = "01234 567894"

            newProfile.save()
            self.profiles.append(newProfile)

    def setupUsefulProfiles(self):
        superUser = models.Profile.objects.create(username="superuser", first_name="Super", last_name="User",
                                                  initials="SU",
                                                  email="superuser@example.com", is_superuser=True, is_active=True,
                                                  is_staff=True)
        superUser.set_password('superuser')
        superUser.save()

        financeUser = models.Profile.objects.create(username="finance", first_name="Finance", last_name="User",
                                                    initials="FU",
                                                    email="financeuser@example.com", is_active=True, is_approved=True)
        financeUser.groups.add(self.finance_group)
        financeUser.groups.add(self.keyholder_group)
        financeUser.set_password('finance')
        financeUser.save()

        hsUser = models.Profile.objects.create(username="hs", first_name="HS", last_name="User",
                                               initials="HSU",
                                               email="hsuser@example.com", is_active=True, is_approved=True)
        hsUser.groups.add(self.hs_group)
        hsUser.groups.add(self.keyholder_group)
        hsUser.set_password('hs')
        hsUser.save()

        keyholderUser = models.Profile.objects.create(username="keyholder", first_name="Keyholder", last_name="User",
                                                      initials="KU",
                                                      email="keyholderuser@example.com", is_active=True, is_approved=True)
        keyholderUser.groups.add(self.keyholder_group)
        keyholderUser.set_password('keyholder')
        keyholderUser.save()

        basicUser = models.Profile.objects.create(username="basic", first_name="Basic", last_name="User", initials="BU",
                                                  email="basicuser@example.com", is_active=True, is_approved=True)
        basicUser.set_password('basic')
        basicUser.save()

    def setupEvents(self):
        names = ["Outdoor Concert", "Hall Open Mic Night", "Festival", "Weekend Event", "Magic Show", "Society Ball",
                 "Evening Show", "Talent Show", "Acoustic Evening", "Hire of Things", "SU Event",
                 "End of Term Show", "Theatre Show", "Outdoor Fun Day", "Summer Carnival", "Open Days", "Magic Show",
                 "Awards Ceremony", "Debating Event", "Club Night", "DJ Evening", "Building Projection",
                 "Choir Concert"]
        descriptions = ["A brief description of the event", "This event is boring", "Probably wont happen",
                        "Warning: this has lots of kit"]
        notes = ["The client came into the office at some point", "Who knows if this will happen",
                 "Probably should check this event", "Maybe not happening", "Run away!"]

        itemOptions = [
            {'name': 'Speakers', 'description': 'Some really really big speakers \n these are very loud', 'quantity': 2,
             'cost': 200.00},
            {'name': 'Projector',
             'description': 'Some kind of video thinamejig, probably with unnecessary processing for free',
             'quantity': 1, 'cost': 500.00},
            {'name': 'Lighting Desk', 'description': 'Cannot provide guarentee that it will work', 'quantity': 1,
             'cost': 200.52},
            {'name': 'Moving lights', 'description': 'Flashy lights, with the copper', 'quantity': 8, 'cost': 50.00},
            {'name': 'Microphones', 'description': 'Make loud noise \n you will want speakers with this', 'quantity': 5,
             'cost': 0.50},
            {'name': 'Sound Mixer Thing', 'description': 'Might be analogue, might be digital', 'quantity': 1,
             'cost': 100.00},
            {'name': 'Electricity', 'description': 'You need this', 'quantity': 1, 'cost': 200.00},
            {'name': 'Crew', 'description': 'Costs nothing, because reasons', 'quantity': 1, 'cost': 0.00},
            {'name': 'Loyalty Discount', 'description': 'Have some negative moneys', 'quantity': 1, 'cost': -50.00}]

        dayDelta = -120  # start adding events from 4 months ago

        for i in range(150):  # Let's add 100 events
            with reversion.create_revision():
                reversion.set_user(random.choice(self.profiles))

                name = names[i % len(names)]

                startDate = datetime.date.today() + datetime.timedelta(days=dayDelta)
                dayDelta = dayDelta + random.randint(0, 3)

                newEvent = models.Event.objects.create(name=name, start_date=startDate)

                if random.randint(0, 2) > 1:  # 1 in 3 have a start time
                    newEvent.start_time = datetime.time(random.randint(15, 20))
                    if random.randint(0, 2) > 1:  # of those, 1 in 3 have an end time on the same day
                        newEvent.end_time = datetime.time(random.randint(21, 23))
                    elif random.randint(0, 1) > 0:  # half of the others finish early the next day
                        newEvent.end_date = newEvent.start_date + datetime.timedelta(days=1)
                        newEvent.end_time = datetime.time(random.randint(0, 5))
                elif random.randint(0, 2) > 1:  # 1 in 3 of the others finish a few days ahead
                    newEvent.end_date = newEvent.start_date + datetime.timedelta(days=random.randint(1, 4))

                if random.randint(0, 6) > 0:  # 5 in 6 have MIC
                    newEvent.mic = random.choice(self.profiles)

                if random.randint(0, 6) > 0:  # 5 in 6 have organisation
                    newEvent.organisation = random.choice(self.organisations)

                if random.randint(0, 6) > 0:  # 5 in 6 have person
                    newEvent.person = random.choice(self.people)

                if random.randint(0, 6) > 0:  # 5 in 6 have venue
                    newEvent.venue = random.choice(self.venues)

                # Could have any status, equally weighted
                newEvent.status = random.choice(
                    [models.Event.BOOKED, models.Event.CONFIRMED, models.Event.PROVISIONAL, models.Event.CANCELLED])

                newEvent.dry_hire = (random.randint(0, 7) == 0)  # 1 in 7 are dry hire

                if random.randint(0, 1) > 0:  # 1 in 2 have description
                    newEvent.description = random.choice(descriptions)

                if random.randint(0, 1) > 0:  # 1 in 2 have notes
                    newEvent.notes = random.choice(notes)

                newEvent.save()

                # Now add some items
                for j in range(random.randint(1, 5)):
                    itemData = itemOptions[random.randint(0, len(itemOptions) - 1)]
                    newItem = models.EventItem.objects.create(event=newEvent, order=j, **itemData)
                    newItem.save()

                while newEvent.sum_total < 0:
                    itemData = itemOptions[random.randint(0, len(itemOptions) - 1)]
                    newItem = models.EventItem.objects.create(event=newEvent, order=j, **itemData)
                    newItem.save()

            with reversion.create_revision():
                reversion.set_user(random.choice(self.profiles))
                if newEvent.start_date < datetime.date.today():  # think about adding an invoice
                    if random.randint(0, 2) > 0:  # 2 in 3 have had paperwork sent to treasury
                        newInvoice = models.Invoice.objects.create(event=newEvent)
                        if newEvent.status is models.Event.CANCELLED:  # void cancelled events
                            newInvoice.void = True
                        elif random.randint(0, 2) > 1:  # 1 in 3 have been paid
                            models.Payment.objects.create(invoice=newInvoice, amount=newInvoice.balance,
                                                          date=datetime.date.today())
            if i == 1 or random.randint(0, 5) > 0:  # Event 1 and 1 in 5 have a RA
                models.RiskAssessment.objects.create(event=newEvent, supervisor_consulted=bool(random.getrandbits(1)), nonstandard_equipment=bool(random.getrandbits(1)),
                                                     nonstandard_use=bool(random.getrandbits(1)),
                                                     contractors=bool(random.getrandbits(1)),
                                                     other_companies=bool(random.getrandbits(1)),
                                                     crew_fatigue=bool(random.getrandbits(1)),
                                                     big_power=bool(random.getrandbits(1)),
                                                     generators=bool(random.getrandbits(1)),
                                                     other_companies_power=bool(random.getrandbits(1)),
                                                     nonstandard_equipment_power=bool(random.getrandbits(1)),
                                                     multiple_electrical_environments=bool(random.getrandbits(1)),
                                                     noise_monitoring=bool(random.getrandbits(1)),
                                                     known_venue=bool(random.getrandbits(1)),
                                                     safe_loading=bool(random.getrandbits(1)),
                                                     safe_storage=bool(random.getrandbits(1)),
                                                     area_outside_of_control=bool(random.getrandbits(1)),
                                                     barrier_required=bool(random.getrandbits(1)),
                                                     nonstandard_emergency_procedure=bool(random.getrandbits(1)),
                                                     special_structures=bool(random.getrandbits(1)),
                                                     suspended_structures=bool(random.getrandbits(1)),
                                                     outside=bool(random.getrandbits(1)))
                if i == 0 or random.randint(0, 1) > 0:  # Event 1 and 1 in 10 have a Checklist
                    models.EventChecklist.objects.create(event=newEvent, power_mic=random.choice(self.profiles), safe_parking=bool(random.getrandbits(1)),
                                                         safe_packing=bool(random.getrandbits(1)), exits=bool(random.getrandbits(1)), trip_hazard=bool(random.getrandbits(1)), warning_signs=bool(random.getrandbits(1)),
                                                         ear_plugs=bool(random.getrandbits(1)), hs_location="Locked away safely",
                                                         extinguishers_location="Somewhere, I forgot", earthing=bool(random.getrandbits(1)), pat=bool(random.getrandbits(1)),
                                                         date=timezone.now(), venue=random.choice(self.venues))

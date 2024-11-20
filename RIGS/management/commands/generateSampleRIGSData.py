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
    events = []
    profiles = models.Profile.objects.all()

    def handle(self, *args, **options):
        print("Generating rigboard data")
        from django.conf import settings

        if not (settings.DEBUG or settings.STAGING):
            raise CommandError('You cannot run this command in production')

        random.seed(
            'Some object to seed the random number generator')  # otherwise it is done by time, which could lead to inconsistant tests

        with transaction.atomic():
            models.VatRate.objects.create(start_at='2014-03-05', rate=0.20, comment='test1')
            self.setup_people()
            self.setup_organisations()
            self.setup_venues()
            self.setup_events()
        print("Done generating rigboard data")

    def setup_people(self):
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
                reversion.set_user(random.choice(models.Profile.objects.all()))
                person = models.Person.objects.create(name=name)

                if i % 3 == 0:
                    person.email = "address@person.com"

                if i % 5 == 0:
                    person.notes = "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua"

                if i % 7 == 0:
                    person.address = "1 Person Test Street \n Demoton \n United States of TEC \n RMRF 567"

                if i % 9 == 0:
                    person.phone = "01234 567894"

                person.save()
                self.people.append(person)

    def setup_organisations(self):
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
                reversion.set_user(random.choice(models.Profile.objects.all()))
                new_organisation = models.Organisation.objects.create(name=name)

                if i % 2 == 0:
                    new_organisation.has_su_account = True

                if i % 3 == 0:
                    new_organisation.email = "address@organisation.com"

                if i % 5 == 0:
                    new_organisation.notes = "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua"

                if i % 7 == 0:
                    new_organisation.address = "1 Organisation Test Street \n Demoton \n United States of TEC \n RMRF 567"

                if i % 9 == 0:
                    new_organisation.phone = "01234 567894"

                new_organisation.save()
                self.organisations.append(new_organisation)

    def setup_venues(self):
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
                new_venue = models.Venue.objects.create(name=name)

                if i % 2 == 0:
                    new_venue.three_phase_available = True

                if i % 3 == 0:
                    new_venue.email = "address@venue.com"

                if i % 5 == 0:
                    new_venue.notes = "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua"

                if i % 7 == 0:
                    new_venue.address = "1 Venue Test Street \n Demoton \n United States of TEC \n RMRF 567"

                if i % 9 == 0:
                    new_venue.phone = "01234 567894"

                new_venue.save()
                self.venues.append(new_venue)

    def setup_events(self):
        names = ["Outdoor Concert", "Hall Open Mic Night", "Festival", "Weekend Event", "Magic Show", "Society Ball",
                 "Evening Show", "Talent Show", "Acoustic Evening", "Hire of Things", "SU Event",
                 "End of Term Show", "Theatre Show", "Outdoor Fun Day", "Summer Carnival", "Open Days", "Magic Show",
                 "Awards Ceremony", "Debating Event", "Club Night", "DJ Evening", "Building Projection",
                 "Choir Concert"]
        descriptions = ["A brief description of the event", "This event is boring", "Probably wont happen",
                        "Warning: this has lots of kit"]
        notes = ["The client came into the office at some point", "Who knows if this will happen",
                 "Probably should check this event", "Maybe not happening", "Run away!"]

        item_options = [
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

        day_delta = -120  # start adding events from 4 months ago

        for i in range(150):  # Let's add 100 events
            with reversion.create_revision():
                reversion.set_user(random.choice(self.profiles))

                name = names[i % len(names)]

                start_date = datetime.date.today() + datetime.timedelta(days=day_delta)
                day_delta = day_delta + random.randint(0, 3)

                new_event = models.Event.objects.create(name=name, start_date=start_date)

                if random.randint(0, 2) > 1:  # 1 in 3 have a start time
                    new_event.start_time = datetime.time(random.randint(15, 20))
                    if random.randint(0, 2) > 1:  # of those, 1 in 3 have an end time on the same day
                        new_event.end_time = datetime.time(random.randint(21, 23))
                    elif random.randint(0, 1) > 0:  # half of the others finish early the next day
                        new_event.end_date = new_event.start_date + datetime.timedelta(days=1)
                        new_event.end_time = datetime.time(random.randint(0, 5))
                elif random.randint(0, 2) > 1:  # 1 in 3 of the others finish a few days ahead
                    new_event.end_date = new_event.start_date + datetime.timedelta(days=random.randint(1, 4))

                if random.randint(0, 6) > 0:  # 5 in 6 have MIC
                    new_event.mic = random.choice(self.profiles)

                if random.randint(0, 6) > 0:  # 5 in 6 have organisation
                    new_event.organisation = random.choice(self.organisations)

                if random.randint(0, 6) > 0:  # 5 in 6 have person
                    new_event.person = random.choice(self.people)

                if random.randint(0, 6) > 0:  # 5 in 6 have venue
                    new_event.venue = random.choice(self.venues)

                # Could have any status, equally weighted
                new_event.status = random.choice(
                    [models.Event.BOOKED, models.Event.CONFIRMED, models.Event.PROVISIONAL, models.Event.CANCELLED])

                new_event.dry_hire = (random.randint(0, 7) == 0)  # 1 in 7 are dry hire

                if random.randint(0, 1) > 0:  # 1 in 2 have description
                    new_event.description = random.choice(descriptions)

                if random.randint(0, 1) > 0:  # 1 in 2 have notes
                    new_event.notes = random.choice(notes)

                new_event.save()

                # Now add some items
                for j in range(random.randint(1, 5)):
                    item_data = item_options[random.randint(0, len(item_options) - 1)]
                    new_item = models.EventItem.objects.create(event=new_event, order=j, **item_data)
                    new_item.save()

                while new_event.sum_total < 0:
                    item_data = item_options[random.randint(0, len(item_options) - 1)]
                    new_item = models.EventItem.objects.create(event=new_event, order=j, **item_data)
                    new_item.save()

            with reversion.create_revision():
                reversion.set_user(random.choice(self.profiles))
                if new_event.start_date < datetime.date.today():  # think about adding an invoice
                    if random.randint(0, 2) > 0:  # 2 in 3 have had paperwork sent to treasury
                        new_invoice = models.Invoice.objects.create(event=new_event)
                        if new_event.status is models.Event.CANCELLED:  # void cancelled events
                            new_invoice.void = True
                        elif random.randint(0, 2) > 1:  # 1 in 3 have been paid
                            models.Payment.objects.create(invoice=new_invoice, amount=new_invoice.balance,
                                                          date=datetime.date.today(), method=random.choice(models.Payment.METHODS)[0])
            if i == 1 or random.randint(0, 5) > 0:  # Event 1 and 1 in 5 have a RA
                models.RiskAssessment.objects.create(event=new_event, supervisor_consulted=bool(random.getrandbits(1)),
                                                     nonstandard_equipment=bool(random.getrandbits(1)),
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
                                                     parking_and_access=bool(random.getrandbits(1)),
                                                     outside=bool(random.getrandbits(1)))
                if i == 0 or random.randint(0, 1) > 0:  # Event 1 and 1 in 10 have a Checklist
                    models.EventChecklist.objects.create(event=new_event,
                                                         safe_parking=bool(random.getrandbits(1)),
                                                         safe_packing=bool(random.getrandbits(1)),
                                                         exits=bool(random.getrandbits(1)),
                                                         trip_hazard=bool(random.getrandbits(1)),
                                                         warning_signs=bool(random.getrandbits(1)),
                                                         ear_plugs=bool(random.getrandbits(1)),
                                                         hs_location="Locked away safely",
                                                         extinguishers_location="Somewhere, I forgot",
                                                         date=timezone.now(), venue=random.choice(self.venues))

from RIGS import models
import pytest
from django.utils import timezone


@pytest.fixture
def basic_event(db):
    event = models.Event.objects.create(name="TE E1", start_date=timezone.now())
    yield event
    event.delete()


@pytest.fixture
def ra(basic_event, admin_user):
    ra = models.RiskAssessment.objects.create(event=basic_event, nonstandard_equipment=False, nonstandard_use=False,
                                              contractors=False, other_companies=False, crew_fatigue=False,
                                              big_power=False, power_mic=admin_user, generators=False,
                                              other_companies_power=False, nonstandard_equipment_power=False,
                                              multiple_electrical_environments=False, noise_monitoring=False,
                                              known_venue=True, safe_loading=True, safe_storage=True,
                                              area_outside_of_control=True, barrier_required=True,
                                              nonstandard_emergency_procedure=True, special_structures=False,
                                              suspended_structures=False, outside=False, parking_and_access=False)
    yield ra
    ra.delete()


@pytest.fixture
def medium_ra(ra):
    ra.big_power = True
    ra.save()
    yield ra
    ra.big_power = False
    ra.save()


@pytest.fixture
def venue(db):
    venue = models.Venue.objects.create(name="Venue 1")
    yield venue
    venue.delete()


@pytest.fixture  # TODO parameterise with Event sizes
def checklist(basic_event, venue, admin_user, ra):
    checklist = models.EventChecklist.objects.create(event=basic_event, safe_parking=False,
                                                     safe_packing=False, exits=False, trip_hazard=False, warning_signs=False,
                                                     ear_plugs=False, hs_location="Locked away safely",
                                                     extinguishers_location="Somewhere, I forgot",
                                                     date=timezone.now(), venue=venue)
    yield checklist
    checklist.delete()


@pytest.fixture
def power_test(basic_event, venue, admin_user, ra):
    power_test = models.PowerTestRecord.objects.create(event=basic_event, venue=venue)
    yield power_test
    power_test.delete()


@pytest.fixture
def many_events(db, admin_user, scope="class"):
    many_events = {
        # produce 7 normal events - 5 current
        1: models.Event.objects.create(name="TE E1", start_date=date.today() + timedelta(days=6),
                                       description="start future no end"),
        2: models.Event.objects.create(name="TE E2", start_date=date.today(), description="start today no end"),
        3: models.Event.objects.create(name="TE E3", start_date=date.today(), end_date=date.today(),
                                       description="start today with end today"),
        4: models.Event.objects.create(name="TE E4", start_date='2014-03-20', description="start past no end"),
        5: models.Event.objects.create(name="TE E5", start_date='2014-03-20', end_date='2014-03-21',
                                       description="start past with end past"),
        6: models.Event.objects.create(name="TE E6", start_date=date.today() - timedelta(days=2),
                                       end_date=date.today() + timedelta(days=2),
                                       description="start past, end future"),
        7: models.Event.objects.create(name="TE E7", start_date=date.today() + timedelta(days=2),
                                       end_date=date.today() + timedelta(days=2),
                                       description="start + end in future"),

        # 2 cancelled - 1 current
        8: models.Event.objects.create(name="TE E8", start_date=date.today() + timedelta(days=2),
                                       end_date=date.today() + timedelta(days=2), status=models.Event.CANCELLED,
                                       description="cancelled in future"),
        9: models.Event.objects.create(name="TE E9", start_date=date.today() - timedelta(days=1),
                                       end_date=date.today() + timedelta(days=2), status=models.Event.CANCELLED,
                                       description="cancelled and started"),

        # 5 dry hire - 3 current
        10: models.Event.objects.create(name="TE E10", start_date=date.today(), dry_hire=True,
                                        description="dryhire today"),
        11: models.Event.objects.create(name="TE E11", start_date=date.today(), dry_hire=True,
                                        checked_in_by=admin_user,
                                        description="dryhire today, checked in"),
        12: models.Event.objects.create(name="TE E12", start_date=date.today() - timedelta(days=1), dry_hire=True,
                                        status=models.Event.BOOKED, description="dryhire past"),
        13: models.Event.objects.create(name="TE E13", start_date=date.today() - timedelta(days=2), dry_hire=True,
                                        checked_in_by=admin_user, description="dryhire past checked in"),
        14: models.Event.objects.create(name="TE E14", start_date=date.today(), dry_hire=True,
                                        status=models.Event.CANCELLED, description="dryhire today cancelled"),

        # 4 non rig - 3 current
        15: models.Event.objects.create(name="TE E15", start_date=date.today(), is_rig=False,
                                        description="non rig today"),
        16: models.Event.objects.create(name="TE E16", start_date=date.today() + timedelta(days=1), is_rig=False,
                                        description="non rig tomorrow"),
        17: models.Event.objects.create(name="TE E17", start_date=date.today() - timedelta(days=1), is_rig=False,
                                        description="non rig yesterday"),
        18: models.Event.objects.create(name="TE E18", start_date=date.today(), is_rig=False,
                                        status=models.Event.CANCELLED,
                                        description="non rig today cancelled"),
    }
    yield many_events
    for event in many_events:
        event.delete()

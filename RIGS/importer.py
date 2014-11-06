__author__ = 'Ghost'
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "PyRIGS.settings")
import django

django.setup()

from django.db import connections
from django.core.exceptions import ObjectDoesNotExist
from django.db.utils import ConnectionDoesNotExist
from django.db import transaction
from RIGS import models
import reversion
from datetime import datetime

def setup_cursor():
    try:
        cursor = connections['legacy'].cursor()
        return cursor
    except ConnectionDoesNotExist:
        print("Legacy database is not configured")
        print(connections._databases)
        return None


def clean_ascii(text):
    return ''.join([i if ord(i) < 128 else '' for i in text])

def import_users():
    cursor = setup_cursor()
    if cursor is None:
        return
    sql = """SELECT `id`, `login`, `email`, `first_name`, `last_name`, `verified`, `initials`, `phone_number` FROM `users`"""
    cursor.execute(sql)
    for row in cursor.fetchall():
        try:
            object = models.Profile.objects.get(pk=row[0])
            object.first_name = row[3]
            object.last_name = row[4]
            object.initials = row[6]
            object.phone = row[7]
            object.save()
            print("Updated " + str(object))
        except ObjectDoesNotExist:
            object = models.Profile(pk=row[0], username=row[1], email=row[2], first_name=row[3], last_name=row[4],
                                    is_active=row[5], initials=row[6], phone=row[7])
            object.set_unusable_password()
            object.save()
            print("Created " + str(object))


def import_people():
    cursor = setup_cursor()
    if cursor is None:
        return
    sql = """SELECT `id`, `name`, `phone`, `email`, `address`, `status` FROM `people`"""
    cursor.execute(sql)
    resp = cursor.fetchall()
    for row in resp:
        email = row[3]
        if email is not "" and "@" not in email:
            email += "@nottingham.ac.uk"

        notes = ""
        if row[5] != "Normal":
            notes = row[5]

        person, created = models.Person.objects.get_or_create(pk=row[0], name=row[1], phone=row[2], email=email,
                                                              address=row[4], notes=notes)
        if created:
            print("Created: " + person.__str__())
            with transaction.atomic(), reversion.create_revision():
                person.save()
        else:
            print("Found: " + person.__str__())


def import_organisations():
    cursor = setup_cursor()
    if cursor is None:
        return
    sql = """SELECT `id`, `name`, `phone`, `address`, `union_account`, `status` FROM `organisations`"""
    cursor.execute(sql)
    for row in cursor.fetchall():
        notes = ""
        if row[5] != "Normal":
            notes = row[5]

        object, created = models.Organisation.objects.get_or_create(pk=row[0], name=row[1], phone=row[2],
                                                                    address=row[3],
                                                                    union_account=row[4], notes=notes)
        if created:
            print("Created: " + object.__str__())
            with transaction.atomic(), reversion.create_revision():
                object.save()
        else:
            print("Found: " + object.__str__())


def import_vat_rates():
    cursor = setup_cursor()
    if cursor is None:
        return
    sql = """SELECT `id`, `start_date`, `start_time`, `comment`, `rate` FROM `vat_rates`"""
    cursor.execute(sql)
    for row in cursor.fetchall():
        start_at = datetime.combine(row[1], row[2])
        object, created = models.VatRate.objects.get_or_create(pk=row[0], start_at=start_at,
                                                               comment=row[3], rate=row[4])
        if created:
            print("Created: " + object.__str__())
            with transaction.atomic(), reversion.create_revision():
                object.save()
        else:
            print("Found: " + object.__str__())


def import_venues(delete=False):
    if delete:
        models.Venue.objects.all().delete()
    cursor = setup_cursor()
    if cursor is None:
        return
    sql = """SELECT `venue`, `threephasepower` FROM `eventdetails` WHERE `venue` IS NOT NULL"""
    cursor.execute(sql)
    for row in cursor.fetchall():
        print(("Searching for %s", row[0]))
        try:
            object = models.Venue.objects.get(name__iexact=row[0])
            if not object.three_phase_available and row[1]:
                with transaction.atomic(), reversion.create_revision():
                    object.three_phase_available = row[1]
                    object.save()
        except ObjectDoesNotExist:
            with transaction.atomic(), reversion.create_revision():
                object = models.Venue(name=row[0], three_phase_available=row[1])
                object.save()

def import_rigs(delete=False):
    if delete:
        models.Event.objects.all().delete()
    cursor = setup_cursor()
    if cursor is None:
        return
    sql = """SELECT r.id, event, person_id, organisation_id, venue, description, status, start_date, start_time, end_date, end_time, access_date, access_time, meet_date, meet_time, meet_info, based_on_id, based_on_type, dry_hire, user_id, payment_method, order_no, payment_received, collectorsid FROM eventdetails AS e INNER JOIN rigs AS r ON e.describable_id = r.id WHERE describable_type = 'Rig' AND venue IS NOT NULL"""
    cursor.execute(sql)
    for row in cursor.fetchall():
        print(row)
        person = models.Person.objects.get(pk=row[2])
        if row[3]:
   	    organisation = models.Organisation.objects.get(pk=row[3])
	else:
	    organisation = None
        venue = models.Venue.objects.get(name__iexact=row[4])
        status = {
            'Booked': models.Event.BOOKED,
            'Provisional': models.Event.PROVISIONAL,
            'Cancelled': models.Event.CANCELLED,
        }
	mic = models.Profile.objects.get(pk=row[19])
	if row[16] and row[17] == "Rig":
	    try:
	        based_on = models.Event.objects.get(pk=row[16])
            except ObjectDoesNotExist:
	        based_on = None
	else:
	    based_on = None
        with transaction.atomic(), reversion.create_revision():
            try:
                object = models.Event.objects.get(pk=row[0])
            except ObjectDoesNotExist:
                object = models.Event(pk=row[0])
            object.name = clean_ascii(row[1])
            object.person = person
            object.organisation = organisation
            object.venue = venue
            object.notes = clean_ascii(row[5])
            object.status = status[row[6]]
            object.start_date = row[7]
            object.start_time = row[8]
            object.end_date = row[9]
            object.end_time = row[10]
	    if row[11] and row[12]:
                object.access_at = datetime.combine(row[11], row[12])
            if row[13] and row[14]:
                object.meet_at = datetime.combine(row[13], row[14])
            object.meet_info = row[15]
            object.based_on = based_on
            object.dry_hire = row[18]
            object.is_rig = True
            object.mic = mic
            object.payment_method = row[20]
            object.purchase_order = row[21]
            object.payment_received = row[22]
            object.collector = row[23]
            object.save()


def import_eventitem(delete=True):
    if delete:
        models.EventItem.objects.all().delete()
    cursor = setup_cursor()
    if cursor is None:
        return
    sql = """SELECT i.id, r.id, i.name, i.description, i.quantity, i.cost, i.sortorder FROM rig_items AS i INNER JOIN eventdetails AS e ON i.eventdetail_id = e.id INNER JOIN rigs AS r ON e.describable_id = r.id"""
    cursor.execute(sql)
    for row in cursor.fetchall():
        with transaction.atomic():
            event = models.Event.objects.get(pk=row[1])
            try:
                object = models.EventItem.objects.get(pk=row[0])
            except:
                object = models.EventItem(pk=row[0])
            object.event = event
            object.name = row[2]
            object.description = row[3]
            object.quantity = row[4]
            object.cost = row[5]
            object.order = row[6]
            object.save()
            with reversion.create_revision():
                event.save()


def main():
    # import_users()
    # import_people()
    # import_organisations()
    # import_vat_rates()
    # import_venues(True)
    # import_events()
    import_rigs(False)


if __name__ == "__main__":
    main()

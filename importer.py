__author__ = 'Ghost'
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "PyRIGS.settings")
import django

django.setup()

from django.db import connection, connections
from django.core.exceptions import ObjectDoesNotExist
from django.db.utils import ConnectionDoesNotExist
from django.db import transaction
from RIGS import models
import reversion
import datetime
import uuid
from multiprocessing import Process

# Slight fix for needing to restablish the connection
connection.close()

def fix_email(email):
    if not (email is None or email is "") and ("@" not in email):
        email += "@nottingham.ac.uk"
    return email


def setup_cursor():
    try:
        cursor = connections['legacy'].cursor()
        return cursor
    except ConnectionDoesNotExist:
        print("Legacy database is not configured")
        print((connections._databases))
        return None


def clean_ascii(text):
    return ''.join([i if ord(i) < 128 else '' for i in text])


def import_users(delete=False):
    if (delete):
        models.Event.objects.get(is_rig=False).delete()
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
            print(("Updated " + str(object)))
        except ObjectDoesNotExist:
            object = models.Profile(pk=row[0], username=row[1], email=row[2], first_name=row[3], last_name=row[4],
                                    is_active=row[5], initials=row[6], phone=row[7])
            object.set_password(uuid.uuid4().hex)
            object.save()
            print(("Created " + str(object)))


def import_people(delete=False):
    if (delete):
        models.Person.objects.all().delete()
    cursor = setup_cursor()
    if cursor is None:
        return
    sql = """SELECT `id`, `name`, `phone`, `email`, `address`, `status` FROM `people`"""
    cursor.execute(sql)
    resp = cursor.fetchall()
    for row in resp:
        pk = row[0]
        name = clean_ascii(row[1])
        phone = clean_ascii(row[2].replace(' ', ''))
        address = clean_ascii(row[4])
        email = clean_ascii(row[3])
        fix_email(email)

        notes = ""
        if row[5] != "Normal":
            notes = row[5]

        print(("Trying %s %s %s" % (pk, name, phone)))
        person, created = models.Person.objects.get_or_create(pk=pk, name=name, phone=phone, email=email,
                                                              address=address, notes=notes)
        if created:
            print(("Created: " + person.__str__()))
            with reversion.create_revision():
                person.save()
        else:
            print(("Found: " + person.__str__()))


def import_organisations(delete=False):
    if (delete):
        models.Organisation.objects.all().delete()
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
            print(("Created: " + object.__str__()))
            with reversion.create_revision():
                object.save()
        else:
            print(("Found: " + object.__str__()))


def import_vat_rates(delete=False):
    if (delete):
        models.VatRate.objects.all().delete()
    cursor = setup_cursor()
    if cursor is None:
        return
    sql = """SELECT `id`, `start_date`, `start_time`, `comment`, `rate` FROM `vat_rates`"""
    cursor.execute(sql)
    for row in cursor.fetchall():
        start_at = datetime.datetime.combine(row[1], row[2])
        object, created = models.VatRate.objects.get_or_create(pk=row[0], start_at=start_at,
                                                               comment=row[3], rate=row[4])
        if created:
            print(("Created: " + object.__str__()))
            with reversion.create_revision():
                object.save()
        else:
            print(("Found: " + object.__str__()))


def import_venues(delete=False):
    if delete:
        models.Venue.objects.all().delete()
    cursor = setup_cursor()
    if cursor is None:
        return
    sql = """SELECT `venue`, `threephasepower` FROM `eventdetails` WHERE `venue` IS NOT NULL GROUP BY `venue`"""
    cursor.execute(sql)
    for row in cursor.fetchall():
        name = row[0].strip()
        print(("Searching for %s", name))
        try:
            object = models.Venue.objects.get(name__iexact=name)
            if not object.three_phase_available and row[1]:
                with reversion.create_revision():
                    object.three_phase_available = row[1]
                    object.save()
        except ObjectDoesNotExist:
            with reversion.create_revision():
                object = models.Venue(name=name, three_phase_available=row[1])
                object.save()


def import_rigs(delete=False):
    if delete:
        models.Event.objects.all().delete()
    cursor = setup_cursor()
    if cursor is None:
        return
    sql = """SELECT r.id, event, person_id, organisation_id, venue, description, status, start_date, start_time, end_date, end_time, access_date, access_time, meet_date, meet_time, meet_info, based_on_id, based_on_type, dry_hire, user_id, payment_method, order_no, payment_received, collectorsid FROM eventdetails AS e INNER JOIN rigs AS r ON e.describable_id = r.id WHERE describable_type = 'Rig' AND `venue` IS NOT NULL"""
    cursor.execute(sql)
    for row in cursor.fetchall():
        print(row)
        person = models.Person.objects.get(pk=row[2])
        if row[3]:
            organisation = models.Organisation.objects.get(pk=row[3])
        else:
            organisation = None
        venue = models.Venue.objects.get(name__iexact=row[4].strip())
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
        with reversion.create_revision():
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
                object.access_at = datetime.datetime.combine(row[11], row[12])
            if row[13] and row[14]:
                object.meet_at = datetime.datetime.combine(row[13], row[14])
            object.meet_info = row[15]
            object.based_on = based_on
            object.dry_hire = row[18]
            object.is_rig = True
            object.mic = mic
            object.payment_method = row[20]
            object.purchase_order = row[21]
            object.payment_received = row[22]
            object.collector = row[23]
            if object.dry_hire and object.end_date < datetime.date.today():
                object.checked_in_by = mic
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
        print(row)
        try:
            event = models.Event.objects.get(pk=row[1])
        except ObjectDoesNotExist:
            continue
        try:
            object = models.EventItem.objects.get(pk=row[0])
        except ObjectDoesNotExist:
            object = models.EventItem(pk=row[0])
        object.event = event
        object.name = clean_ascii(row[2])
        object.description = clean_ascii(row[3])
        object.quantity = row[4]
        object.cost = row[5]
        object.order = row[6] if row[6] else 0
        object.save()
        with reversion.create_revision():
            event.save()


def import_nonrigs(delete=False):
    if (delete):
        try:
            models.Event.objects.filter(is_rig=False).delete()
        except:
            pass
    cursor = setup_cursor()
    if cursor is None:
        return
    sql = """SELECT name, start_date, start_time, end_date, end_time, description, user_id FROM non_rigs WHERE active = 1;"""
    cursor.execute(sql)
    for row in cursor.fetchall():
        print(row)
        mic = models.Profile.objects.get(pk=row[6])
        object = models.Event()
        object.name = row[0]
        object.start_date = row[1]
        object.start_time = row[2]
        object.end_date = row[3]
        object.end_time = row[4]
        object.description = row[5]
        object.is_rig = False
        object.mic = mic
        print(object)
        object.save()


def import_invoices(delete=False):
    if delete:
        try:
            models.Invoice.objects.all().delete()
            models.Payment.objects.all().delete()
        except:
            pass
    cursor = setup_cursor()
    if cursor is None:
        return
    sql = """SELECT id, rig_id, invoice_date, payment_date, amount FROM invoices"""
    cursor.execute(sql)
    for row in cursor.fetchall():
        print(row)
        print(row[1])
        try:
            event = models.Event.objects.get(pk=row[1])
        except ObjectDoesNotExist:
            print("Event %d not found" % row[1])
            continue
        print(event)

        try:
            invoice = models.Invoice.objects.get(event=event)
        except ObjectDoesNotExist:
            invoice = models.Invoice(pk=row[0], event=event)
        invoice.save()
        invoice.invoice_date = row[2]
        invoice.save()
        print(invoice)

        if row[3]:
            try:
                payment = models.Payment.objects.get(invoice=invoice)
            except ObjectDoesNotExist:
                payment = models.Payment(invoice=invoice)
            if row[4] >= event.sum_total:
                payment.amount = event.sum_total
            else:
                payment.amount = row[4]
            payment.date = row[3]
            payment.save()
            print(payment)

        if invoice.invoice_date < (datetime.date.today() - datetime.timedelta(days=365)) and invoice.balance:
            p2 = models.Payment(amount=invoice.balance)
            p2.invoice = invoice
            p2.method = payment.ADJUSTMENT
            p2.date = datetime.date.today()
            p2.save()

@transaction.atomic
def main():
    # processs = []
    # processs.append(Process(target=import_users))
    # processs.append(Process(target=import_people, args=(True,)))
    # processs.append(Process(target=import_organisations, args=(True,)))
    # processs.append(Process(target=import_vat_rates, args=(True,)))
    # processs.append(Process(target=import_venues, args=(True,)))
    
    #  # Start all processs
    # [x.start() for x in processs]
    # # Wait for all processs to finish
    # [x.join() for x in processs]

    import_users()
    import_people(True)
    import_organisations(True)
    import_vat_rates(True)
    import_venues(True)
    
    import_rigs(True)
    import_eventitem(True)
    import_invoices(True)

    # Do this before doing non rigs else it gets ugly
    sql = "SELECT setval(\'\"RIGS_%s_id_seq\"\', (SELECT MAX(id) FROM \"RIGS_%s\"));" % ('event', 'event')
    cursor = connections['default'].cursor()
    cursor.execute(sql)
    import_nonrigs(False)

    sequences = ['profile', 'person', 'organisation', 'vatrate', 'venue', 'event', 'eventitem', 'invoice', 'payment']
    for seq in sequences:
        sql = "SELECT setval(\'\"RIGS_%s_id_seq\"\', (SELECT MAX(id) FROM \"RIGS_%s\"));" % (seq, seq)
        cursor = connections['default'].cursor()
        cursor.execute(sql)

if __name__ == "__main__":
    main()

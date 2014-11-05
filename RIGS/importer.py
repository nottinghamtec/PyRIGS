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


def main():
    # import_people()
    # import_organisations()
    import_vat_rates()


if __name__ == "__main__":
    main()

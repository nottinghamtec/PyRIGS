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
    i=0
    for row in resp:
        if (i+1) > 1:
            break
        email = row[3]
        if email is not "" and "@" not in email:
            email += "@nottingham.ac.uk"

        notes = ""
        if row[5] !=  "Normal":
            notes = row[5]

        person, created = models.Person.objects.get_or_create(pk=row[0], name=row[1], phone=row[2], email=email, address=row[4], notes=notes)
        if created:
            print("Created: " + person.__unicode__())
            with transaction.atomic(), reversion.create_revision():
                person.save()
        else:
            print("Found: " + person.__unicode__())

def main():
    import_people()

if __name__=="__main__":
    main()
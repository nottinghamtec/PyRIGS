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

    profiles = []
    keyholder_group = None
    finance_group = None
    hs_group = None

    def handle(self, *args, **options):
        print("Generating sample user data")
        from django.conf import settings

        if not (settings.DEBUG or settings.STAGING):
            raise CommandError('You cannot run this command in production')

        random.seed(
            'Some object to seed the random number generator')  # otherwise it is done by time, which could lead to inconsistent tests

        with transaction.atomic():
            self.setup_groups()
            self.setup_useful_profiles()
            self.setup_generic_profiles()
        print("Done generating sample user data")

    def setup_groups(self):
        self.keyholder_group = Group.objects.create(name='Keyholders')
        self.finance_group = Group.objects.create(name='Finance')
        self.hs_group = Group.objects.create(name='H&S')

        keyholder_perms = ["add_event", "change_event", "view_event",
                           "add_eventitem", "change_eventitem", "delete_eventitem",
                           "add_organisation", "change_organisation", "view_organisation",
                           "add_person", "change_person", "view_person", "view_profile",
                           "add_venue", "change_venue", "view_venue",
                           "add_asset", "change_asset", "delete_asset",
                           "view_asset", "view_supplier", "change_supplier", "asset_finance",
                           "add_supplier", "view_cabletype", "change_cabletype",
                           "add_cabletype", "view_eventchecklist", "change_eventchecklist",
                           "add_eventchecklist", "view_riskassessment", "change_riskassessment",
                           "add_riskassessment"]
        finance_perms = keyholder_perms + ["add_invoice", "change_invoice", "view_invoice",
                                           "add_payment", "change_payment", "delete_payment"]
        hs_perms = keyholder_perms + ["review_riskassessment", "review_eventchecklist"]

        for permId in keyholder_perms:
            self.keyholder_group.permissions.add(Permission.objects.get(codename=permId))

        for permId in finance_perms:
            self.finance_group.permissions.add(Permission.objects.get(codename=permId))

        for permId in hs_perms:
            self.hs_group.permissions.add(Permission.objects.get(codename=permId))
        self.keyholder_group.save()
        self.finance_group.save()
        self.hs_group.save()

    def setup_generic_profiles(self):
        names = ["Clara Oswin Oswald", "Rory Williams", "Amy Pond", "River Song", "Martha Jones", "Donna Noble",
                 "Jack Harkness", "Mickey Smith", "Rose Tyler"]
        for i, name in enumerate(names):
            new_profile = models.Profile.objects.create(username=name.replace(" ", ""), first_name=name.split(" ")[0],
                                                        last_name=name.split(" ")[-1],
                                                        email=name.replace(" ", "") + "@example.com",
                                                        initials="".join([j[0].upper() for j in name.split()]))
            if i % 2 == 0:
                new_profile.phone = "01234 567894"

            new_profile.save()
            self.profiles.append(new_profile)

    def setup_useful_profiles(self):
        super_user = models.Profile.objects.create_superuser(username="superuser",
                                                             email="superuser@example.com", password="superuser", first_name="Super", last_name="User",
                                                             initials="SU", is_active=True)
        super_user.save()

        finance_user = models.Profile.objects.create_user(username="finance",
                                                          email="financeuser@example.com", password="finance", first_name="Finance", last_name="User",
                                                          initials="FU", is_active=True, is_approved=True)
        finance_user.groups.add(self.finance_group)
        finance_user.groups.add(self.keyholder_group)
        finance_user.save()

        hs_user = models.Profile.objects.create_user(username="hs",
                                                     email="hsuser@example.com", password="hs", first_name="HS", last_name="User",
                                                     initials="HSU", is_active=True, is_approved=True)
        hs_user.groups.add(self.hs_group)
        hs_user.groups.add(self.keyholder_group)
        hs_user.save()

        keyholder_user = models.Profile.objects.create_user(username="keyholder",
                                                            email="keyholderuser@example.com", password="keyholder", first_name="Keyholder", last_name="User",
                                                            initials="KU", is_active=True,
                                                            is_approved=True)
        keyholder_user.groups.add(self.keyholder_group)
        keyholder_user.save()

        basic_user = models.Profile.objects.create_user(username="basic",
                                                        email="basicuser@example.com", password="basic", first_name="Basic", last_name="User",
                                                        initials="BU", is_active=True, is_approved=True)

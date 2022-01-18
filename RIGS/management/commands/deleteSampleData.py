from django.core.management.base import BaseCommand, CommandError

from django.contrib.auth.models import Group
from assets import models
from RIGS import models as rigsmodels
from training import models as tmodels


class Command(BaseCommand):
    help = 'Deletes testing sample data'

    def handle(self, *args, **kwargs):
        from django.conf import settings

        if not settings.DEBUG:
            raise CommandError('You cannot run this command in production')

        self.delete_objects(models.AssetCategory)
        self.delete_objects(models.AssetStatus)
        self.delete_objects(models.Supplier)
        self.delete_objects(models.Connector)
        self.delete_objects(models.Asset)
        self.delete_objects(rigsmodels.VatRate)
        self.delete_objects(rigsmodels.Profile)
        self.delete_objects(rigsmodels.Person)
        self.delete_objects(rigsmodels.Organisation)
        self.delete_objects(rigsmodels.Venue)
        self.delete_objects(Group)
        self.delete_objects(rigsmodels.Event)
        self.delete_objects(rigsmodels.EventItem)
        self.delete_objects(rigsmodels.Invoice)
        self.delete_objects(rigsmodels.Payment)
        self.delete_objects(rigsmodels.RiskAssessment)
        self.delete_objects(rigsmodels.EventChecklist)
        self.delete_objects(tmodels.TrainingCategory)
        self.delete_objects(tmodels.TrainingItem)
        self.delete_objects(tmodels.TrainingLevel)
        self.delete_objects(tmodels.TrainingItemQualification)
        self.delete_objects(tmodels.TrainingLevelRequirement)

    def delete_objects(self, model):
        for obj in model.objects.all():
            obj.delete()

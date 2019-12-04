from django.core.management.base import BaseCommand, CommandError

from assets import models


class Command(BaseCommand):
    help = 'Deletes testing sample data'

    def handle(self, *args, **kwargs):
        from django.conf import settings

        if not (settings.DEBUG):
            raise CommandError('You cannot run this command in production')

        self.delete_objects(models.AssetCategory)
        self.delete_objects(models.AssetStatus)
        self.delete_objects(models.Supplier)
        self.delete_objects(models.Connector)
        self.delete_objects(models.Asset)

    def delete_objects(self, model):
        for object in model.objects.all():
            object.delete()

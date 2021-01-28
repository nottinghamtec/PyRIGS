from django.core.management.base import BaseCommand, CommandError

from assets import models


def delete_objects(model):
    for object in model.objects.all():
        object.delete()


class Command(BaseCommand):
    help = 'Deletes testing sample data'

    def handle(self, *args, **kwargs):
        from django.conf import settings

        if not (settings.DEBUG):
            raise CommandError('You cannot run this command in production')

        delete_objects(models.AssetCategory)
        delete_objects(models.AssetStatus)
        delete_objects(models.Supplier)
        delete_objects(models.Connector)
        delete_objects(models.Asset)

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Adds sample data to use for testing'
    can_import_settings = True

    def handle(self, *args, **options):
        call_command('generateSampleRIGSData')
        call_command('generateSampleAssetsData')

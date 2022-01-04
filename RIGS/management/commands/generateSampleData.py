from django.core.management import call_command
from django.core.management.base import BaseCommand

from RIGS import models


class Command(BaseCommand):
    help = 'Adds sample data to use for testing'
    can_import_settings = True

    def handle(self, *args, **options):
        call_command('generateSampleUserData')
        call_command('generateSampleRIGSData')
        call_command('generateSampleAssetsData')
        call_command('import_old_db')
        call_command('generate_sample_training_users')

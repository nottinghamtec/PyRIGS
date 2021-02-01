from django.core.management import call_command
from django.core.management.base import BaseCommand
import time

class Command(BaseCommand):
    help = 'Adds sample data to use for testing'
    can_import_settings = True

    def handle(self, *args, **options):
        begin = time.time()
        call_command('generateSampleRIGSData')
        call_command('generateSampleAssetsData')
        end = time.time()
        print(f"Total runtime of the program is {end - begin}")

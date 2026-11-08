from django.core.management.base import BaseCommand

from PyRIGS.search import refresh_vocabulary


class Command(BaseCommand):
    help = "Rebuilds the list of known words that search uses for its 'Did you mean' suggestions"

    def handle(self, *args, **options):
        words = refresh_vocabulary()
        self.stdout.write(self.style.SUCCESS(f"Search vocabulary now holds {words} words"))

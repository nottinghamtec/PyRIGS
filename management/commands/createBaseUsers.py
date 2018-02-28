from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User

from django.conf import settings


class Command(BaseCommand):
    help = 'Creates a super user'

    def handle(self, *args, **options):
        if not (settings.DEBUG or settings.STAGING):
            raise CommandError('You cannot run this command in production')

        self.create_user_object('super', True, True)
        self.create_user_object('staff', True)
        self.create_user_object('basic')

    def create_user_object(self, name, staff=False, superuser=False):
        user, created = User.objects.get_or_create(
            username=name, defaults={'email': '{}@{}.com'.format(name, name),
                                     'first_name': name.title(), 'last_name': 'User', 'is_superuser': superuser,
                                     'is_staff': staff})

        if created:
            user.set_password(name)
            user.save()
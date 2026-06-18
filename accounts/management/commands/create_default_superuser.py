import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.core.management.utils import get_random_secret_key


class Command(BaseCommand):
    help = 'Creates default superuser if none exists'

    def handle(self, *args, **kwargs):
        User = get_user_model()
        if not User.objects.filter(is_superuser=True).exists():
            password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')
            generated = password is None
            if generated:
                password = get_random_secret_key()
            User.objects.create_superuser(
                username=os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin'),
                email=os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@ssbikez.com'),
                password=password,
            )
            if generated:
                self.stdout.write(self.style.WARNING(
                    f'Superuser created with a generated password: {password}\n'
                    'Log in and change it immediately — set DJANGO_SUPERUSER_PASSWORD '
                    'to control this on future deploys.'
                ))
            else:
                self.stdout.write('Superuser created.')
        else:
            self.stdout.write('Superuser already exists.')

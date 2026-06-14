import os

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = 'Creates default superuser if none exists'

    def handle(self, *args, **kwargs):
        User = get_user_model()
        if not User.objects.filter(is_superuser=True).exists():
            password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'SSBikez@2026')
            User.objects.create_superuser(
                username=os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin'),
                email=os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@ssbikez.com'),
                password=password,
            )
            self.stdout.write('Superuser created.')
        else:
            self.stdout.write('Superuser already exists.')

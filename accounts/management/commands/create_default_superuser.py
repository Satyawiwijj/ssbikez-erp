from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = 'Creates default superuser if none exists'

    def handle(self, *args, **kwargs):
        User = get_user_model()
        if not User.objects.filter(is_superuser=True).exists():
            User.objects.create_superuser(
                username='admin',
                email='admin@ssbikez.com',
                password='SSBikez@2026'
            )
            self.stdout.write('Superuser created.')
        else:
            self.stdout.write('Superuser already exists.')

from datetime import date, timedelta

from django.core.management.base import BaseCommand

from customer_vehicles.models import CustomerVehicle
from service.models import ServiceReminder, JobCardRevisit
from vas.models import AMCPackage


class Command(BaseCommand):
    help = 'Generate service reminders for CRE team'

    def handle(self, *args, **kwargs):
        today = date.today()
        created = 0

        # Free service reminders from revisit schedule
        for jr in JobCardRevisit.objects.filter(
            next_service_date__lte=today + timedelta(days=7),
            next_service_date__gte=today
        ).select_related('job_card__customer_vehicle'):
            cv = jr.job_card.customer_vehicle
            exists = ServiceReminder.objects.filter(
                customer_vehicle=cv,
                reminder_type='free_service',
                reminder_date=jr.next_service_date,
                status='pending'
            ).exists()
            if not exists:
                ServiceReminder.objects.create(
                    customer_vehicle=cv,
                    reminder_date=jr.next_service_date,
                    reminder_type='free_service',
                    due_km=jr.next_service_km,
                    notes=f'Free service due at {jr.next_service_km}km'
                )
                created += 1

        # Insurance expiry reminders
        for cv in CustomerVehicle.objects.filter(
            insurance_expiry__lte=today + timedelta(days=30),
            insurance_expiry__gte=today
        ):
            exists = ServiceReminder.objects.filter(
                customer_vehicle=cv,
                reminder_type='insurance_expiry',
                status='pending'
            ).exists()
            if not exists:
                reminder_date = cv.insurance_expiry - timedelta(days=7)
                ServiceReminder.objects.create(
                    customer_vehicle=cv,
                    reminder_date=max(reminder_date, today),
                    reminder_type='insurance_expiry',
                    notes=f'Insurance expires on {cv.insurance_expiry}'
                )
                created += 1

        # Warranty expiry reminders
        for cv in CustomerVehicle.objects.filter(
            warranty_end_date__lte=today + timedelta(days=30),
            warranty_end_date__gte=today
        ):
            exists = ServiceReminder.objects.filter(
                customer_vehicle=cv,
                reminder_type='warranty_expiry',
                status='pending'
            ).exists()
            if not exists:
                ServiceReminder.objects.create(
                    customer_vehicle=cv,
                    reminder_date=today,
                    reminder_type='warranty_expiry',
                    notes=f'Warranty expires on {cv.warranty_end_date}'
                )
                created += 1

        # AMC renewal reminders
        for amc in AMCPackage.objects.filter(
            end_date__lte=today + timedelta(days=30),
            end_date__gte=today,
            status='active'
        ).select_related('customer_vehicle'):
            cv = amc.customer_vehicle
            exists = ServiceReminder.objects.filter(
                customer_vehicle=cv,
                reminder_type='amc_renewal',
                status='pending'
            ).exists()
            if not exists:
                ServiceReminder.objects.create(
                    customer_vehicle=cv,
                    reminder_date=today,
                    reminder_type='amc_renewal',
                    notes=f'AMC expires on {amc.end_date}'
                )
                created += 1

        self.stdout.write(self.style.SUCCESS(f'Created {created} service reminders'))

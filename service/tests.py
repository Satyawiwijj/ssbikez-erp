"""
Regression tests for the ownership-check gaps found in service module views
during the ownership-consistency audit rounds: quick-action "side door"
views (jobcard_status_update) and a legacy child-record's own
update/delete views (labor_charge_update/_delete) that mutate data tied to
a JobCard without going through the JobCard's own protected edit view.
"""
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import Role, User
from customer_vehicles.models import CustomerVehicle
from customers.models import BikeModel, Customer, VehicleStock
from service.models import JobCard, LaborCharge


def _make_job_card(advisor, suffix=''):
    customer = Customer.objects.create(full_name=f'Svc Customer{suffix}', phone=f'600000000{suffix or "0"}')
    bike_model = BikeModel.objects.create(brand='TVS', model_name=f'Jupiter{suffix}', ex_showroom_price=Decimal('90000'))
    vehicle = VehicleStock.objects.create(bike_model=bike_model, chassis_no=f'SVCCH{suffix or "0"}')
    customer_vehicle = CustomerVehicle.objects.create(customer=customer, vehicle=vehicle)
    return JobCard.objects.create(customer_vehicle=customer_vehicle, service_advisor=advisor)


class JobCardStatusUpdateOwnershipTests(TestCase):
    """jobcard_status_update is a quick-action side door onto JobCard -- it
    must enforce the same ownership check as the main edit view, not let any
    authorized service-namespace user change a colleague's job card status."""

    @classmethod
    def setUpTestData(cls):
        advisor_role, _ = Role.objects.get_or_create(role_name='Service Advisor')
        cls.owner = User.objects.create_user(
            username='svc_owner', email='svcowner@example.com', password='Test-Pass-123!', role=advisor_role,
        )
        cls.other = User.objects.create_user(
            username='svc_other', email='svcother@example.com', password='Test-Pass-123!', role=advisor_role,
        )

    def test_non_owner_cannot_change_status(self):
        job_card = _make_job_card(self.owner, '1')
        self.client.force_login(self.other)
        response = self.client.post(
            reverse('service:jobcard_status_update', args=[job_card.pk]),
            {'service_status': JobCard.ServiceStatus.IN_BAY},
        )
        self.assertEqual(response.status_code, 403)
        job_card.refresh_from_db()
        self.assertEqual(job_card.service_status, JobCard.ServiceStatus.PENDING)

    def test_owner_can_change_status(self):
        job_card = _make_job_card(self.owner, '2')
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse('service:jobcard_status_update', args=[job_card.pk]),
            {'service_status': JobCard.ServiceStatus.IN_BAY},
        )
        self.assertEqual(response.status_code, 302)
        job_card.refresh_from_db()
        self.assertEqual(job_card.service_status, JobCard.ServiceStatus.IN_BAY)


class LaborChargeOwnershipTests(TestCase):
    """LaborCharge's own update/delete views, checked via the parent
    JobCard's service_advisor -- same ownership convention as everywhere
    else, closing a gap that used to let any service user edit/delete a
    colleague's labor-charge line."""

    @classmethod
    def setUpTestData(cls):
        advisor_role, _ = Role.objects.get_or_create(role_name='Service Advisor')
        cls.owner = User.objects.create_user(
            username='lc_owner', email='lcowner@example.com', password='Test-Pass-123!', role=advisor_role,
        )
        cls.other = User.objects.create_user(
            username='lc_other', email='lcother@example.com', password='Test-Pass-123!', role=advisor_role,
        )

    def test_non_owner_cannot_update(self):
        job_card = _make_job_card(self.owner, '3')
        charge = LaborCharge.objects.create(job_card=job_card, service_name='Oil Change', labor_cost=Decimal('200'))
        self.client.force_login(self.other)
        response = self.client.post(
            reverse('service:labor_charge_update', args=[charge.pk]),
            {'service_name': 'Tampered', 'labor_cost': '9999'},
        )
        self.assertEqual(response.status_code, 403)
        charge.refresh_from_db()
        self.assertEqual(charge.service_name, 'Oil Change')

    def test_non_owner_cannot_delete(self):
        job_card = _make_job_card(self.owner, '4')
        charge = LaborCharge.objects.create(job_card=job_card, service_name='Chain Lube', labor_cost=Decimal('100'))
        self.client.force_login(self.other)
        response = self.client.post(reverse('service:labor_charge_delete', args=[charge.pk]))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(LaborCharge.objects.filter(pk=charge.pk).exists())

    def test_owner_can_update_and_delete(self):
        job_card = _make_job_card(self.owner, '5')
        charge = LaborCharge.objects.create(job_card=job_card, service_name='Brake Pad', labor_cost=Decimal('300'))
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse('service:labor_charge_update', args=[charge.pk]),
            {'job_card': job_card.pk, 'service_name': 'Brake Pad Replacement', 'labor_cost': '350'},
        )
        self.assertEqual(response.status_code, 302)
        charge.refresh_from_db()
        self.assertEqual(charge.service_name, 'Brake Pad Replacement')

        response = self.client.post(reverse('service:labor_charge_delete', args=[charge.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(LaborCharge.objects.filter(pk=charge.pk).exists())

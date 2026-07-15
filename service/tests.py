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


from django.test import TestCase as _TestCase
from django.urls import reverse as _reverse

from service.models import JobCard as _JobCard


def _checklist_management_forms():
    payload = {}
    for prefix in ('complaints', 'observations', 'engine', 'lights', 'chasis'):
        payload.update({
            f'{prefix}-TOTAL_FORMS': '0', f'{prefix}-INITIAL_FORMS': '0',
            f'{prefix}-MIN_NUM_FORMS': '0', f'{prefix}-MAX_NUM_FORMS': '1000',
        })
    return payload


class JobCardCRUDTests(TestCase):

    def setUp(self):
        advisor_role, _ = Role.objects.get_or_create(role_name='Service Advisor')
        self.user = User.objects.create_user(username='jc_admin', email='jcadmin@example.com', password='Test-Pass-123!', role=advisor_role)
        self.client.force_login(self.user)
        self.job_card = _make_job_card(self.user, 'CRUD1')

    def test_create_with_no_checklist_rows(self):
        payload = {
            'customer_vehicle': self.job_card.customer_vehicle_id, 'service_status': JobCard.ServiceStatus.PENDING,
        }
        payload.update(_checklist_management_forms())
        response = self.client.post(_reverse('service:jobcard_create'), payload)
        self.assertEqual(response.status_code, 302)

    def test_detail_and_list_render(self):
        response = self.client.get(_reverse('service:jobcard_detail', args=[self.job_card.pk]))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(_reverse('service:jobcard_list'))
        self.assertEqual(response.status_code, 200)


from service.models import WarrantyClaim as _WarrantyClaim, WaterWashDone as _WaterWashDone


class WaterWashDoneCRUDTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser(username='ww_admin', email='wwadmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)
        self.job_card = _make_job_card(self.user, 'WW1')

    def test_create_then_detail_then_submit(self):
        response = self.client.post(reverse('service:water_wash_create'), {'job_card': self.job_card.pk})
        self.assertEqual(response.status_code, 302)
        ww = _WaterWashDone.objects.get(job_card=self.job_card)

        response = self.client.get(reverse('service:water_wash_detail', args=[ww.pk]))
        self.assertEqual(response.status_code, 200)

        response = self.client.post(reverse('service:water_wash_submit', args=[ww.pk]))
        self.assertEqual(response.status_code, 302)
        ww.refresh_from_db()
        self.assertEqual(ww.docstatus, 1)


class WarrantyClaimCRUDTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser(username='wc_admin', email='wcadmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)
        self.job_card = _make_job_card(self.user, 'WC1')

    def test_create_then_list(self):
        response = self.client.post(reverse('service:warranty_claim_create'), {
            'job_card': self.job_card.pk, 'description': 'Engine noise under warranty',
            'claimed_amount': '5000', 'approved_amount': '0', 'status': 'submitted',
        })
        self.assertEqual(response.status_code, 302)
        claim = _WarrantyClaim.objects.get(job_card=self.job_card)
        self.assertTrue(claim.claim_number)

        response = self.client.get(reverse('service:warranty_claim_list'))
        self.assertEqual(response.status_code, 200)


class BayInCreationCRUDTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser(username='bayin_admin', email='bayinadmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)
        self.job_card = _make_job_card(self.user, 'BAYIN1')

    def test_create(self):
        response = self.client.post(reverse('service:bay_in_create'), {
            'job_card': self.job_card.pk, 'date_time': '2020-01-01T10:00',
        })
        self.assertEqual(response.status_code, 302)


class FinalInspectionCreateTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser(username='fi_admin', email='fiadmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)
        self.job_card = _make_job_card(self.user, 'FI1')

    def test_create(self):
        response = self.client.post(reverse('service:final_inspection_create'), {
            'job_card': self.job_card.pk, 'final_inspection_remarks': 'All checks OK',
        })
        self.assertEqual(response.status_code, 302)


class OutworkEntryIssueCreateTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser(username='oei_admin', email='oeiadmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)
        self.job_card = _make_job_card(self.user, 'OEI1')
        from masters.models import Supplier
        self.vendor = Supplier.objects.create(supplier_name='Outwork Vendor Co')

    def test_create_with_no_child_rows(self):
        payload = {'job_card': self.job_card.pk, 'vendor_name': self.vendor.pk}
        for prefix in ('work', 'spares'):
            payload.update({
                f'{prefix}-TOTAL_FORMS': '0', f'{prefix}-INITIAL_FORMS': '0',
                f'{prefix}-MIN_NUM_FORMS': '0', f'{prefix}-MAX_NUM_FORMS': '1000',
            })
        response = self.client.post(reverse('service:outwork_issue_create'), payload)
        self.assertEqual(response.status_code, 302)


class LaborChargesAlterationCreateTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser(username='lca_admin', email='lcaadmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)
        self.job_card = _make_job_card(self.user, 'LCA1')

    def test_create_with_no_child_rows(self):
        payload = {'job_card': self.job_card.pk}
        for prefix in ('labor', 'spares'):
            payload.update({
                f'{prefix}-TOTAL_FORMS': '0', f'{prefix}-INITIAL_FORMS': '0',
                f'{prefix}-MIN_NUM_FORMS': '0', f'{prefix}-MAX_NUM_FORMS': '1000',
            })
        response = self.client.post(reverse('service:labor_alteration_create'), payload)
        self.assertEqual(response.status_code, 302)

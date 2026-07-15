"""
Regression tests for VehicleMasterSettings' submit-time batch chassis
intake -- the real "closes the confirmed Django gap (no bulk VehicleStock
creation existed before this phase)" side effect, including the
duplicate-chassis skip-not-crash behavior.
"""
from decimal import Decimal

from django.test import TestCase

from customers.models import BikeModel, VehicleMasterSettings, VehicleMasterSettingsItem, VehicleStock


class VehicleMasterSettingsSubmitTests(TestCase):

    def setUp(self):
        self.bike_model = BikeModel.objects.create(brand='Hero', model_name='Splendor', ex_showroom_price=Decimal('75000'))

    def test_submit_creates_a_vehicle_stock_row_per_item(self):
        master = VehicleMasterSettings.objects.create(vehicle=self.bike_model)
        VehicleMasterSettingsItem.objects.create(
            master=master, model='Splendor', chasis_no='CH-BATCH-001', code='C001', engine='EN001', color='Black', book_no='B001',
        )
        VehicleMasterSettingsItem.objects.create(
            master=master, model='Splendor', chasis_no='CH-BATCH-002', code='C002', engine='EN002', color='Red', book_no='B002',
        )
        self.assertEqual(VehicleStock.objects.filter(chassis_no__startswith='CH-BATCH-').count(), 0)
        master.docstatus = VehicleMasterSettings.DocStatus.SUBMITTED
        master.save()
        stock = VehicleStock.objects.filter(chassis_no__startswith='CH-BATCH-')
        self.assertEqual(stock.count(), 2)
        self.assertEqual(set(stock.values_list('engine_no', flat=True)), {'EN001', 'EN002'})

    def test_duplicate_chassis_on_a_second_batch_is_skipped_not_crashed(self):
        first = VehicleMasterSettings.objects.create(vehicle=self.bike_model)
        VehicleMasterSettingsItem.objects.create(
            master=first, model='Splendor', chasis_no='CH-DUP-001', code='C001', engine='EN001', color='Black', book_no='B001',
        )
        first.docstatus = VehicleMasterSettings.DocStatus.SUBMITTED
        first.save()
        self.assertEqual(VehicleStock.objects.filter(chassis_no='CH-DUP-001').count(), 1)

        second = VehicleMasterSettings.objects.create(vehicle=self.bike_model)
        VehicleMasterSettingsItem.objects.create(
            master=second, model='Splendor', chasis_no='CH-DUP-001', code='C001', engine='EN999', color='Blue', book_no='B999',
        )
        second.docstatus = VehicleMasterSettings.DocStatus.SUBMITTED
        second.save()  # must not raise IntegrityError on the unique chassis_no
        self.assertEqual(VehicleStock.objects.filter(chassis_no='CH-DUP-001').count(), 1)


from django.urls import reverse as _reverse

from accounts.models import User as _User


class CustomerCRUDTests(TestCase):

    def setUp(self):
        self.user = _User.objects.create_superuser(username='cust_admin', email='custadmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)

    def test_create_then_list(self):
        from customers.models import Customer
        response = self.client.post(_reverse('customers:customer_create'), {
            'full_name': 'Ravi Kumar', 'phone': '9600000001',
        })
        self.assertEqual(response.status_code, 302)
        customer = Customer.objects.get(phone='9600000001')

        response = self.client.get(_reverse('customers:customer_list'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(customer, response.context['customers'])


class BikeModelCRUDTests(TestCase):

    def setUp(self):
        self.user = _User.objects.create_superuser(username='bike_admin', email='bikeadmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)

    def test_create_then_list(self):
        response = self.client.post(_reverse('customers:bike_model_create'), {
            'brand': 'Hero', 'model_name': 'Xtreme 160R', 'fuel_type': 'petrol', 'ex_showroom_price': '135000',
        })
        self.assertEqual(response.status_code, 302)
        model = BikeModel.objects.get(model_name='Xtreme 160R')

        response = self.client.get(_reverse('customers:bike_model_list'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(model, response.context['bike_models'])

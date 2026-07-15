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

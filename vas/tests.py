"""
Regression tests for the VAS stock-safety guard and auto-invoice-on-submit
behavior added in Phase 11b: submitting an AMC/RSA/Protection-Plus package
must be blocked when the plan type has zero stock, and a submit with a real
sales_order must create a matching billing.Invoice exactly once.
"""
from decimal import Decimal

from django.test import TestCase

from accounts.models import User
from customer_vehicles.models import CustomerVehicle
from customers.models import BikeModel, Customer, VehicleStock
from sales.models import VehicleSalesOrder
from vas.models import AMCPackage, AMCType, VASStockLedger


def _make_customer_vehicle(suffix=''):
    customer = Customer.objects.create(full_name=f'VAS Customer{suffix}', phone=f'800000000{suffix or "0"}')
    bike_model = BikeModel.objects.create(
        brand='Yamaha', model_name=f'FZ{suffix}', ex_showroom_price=Decimal('120000'),
    )
    vehicle = VehicleStock.objects.create(bike_model=bike_model, chassis_no=f'CH{suffix or "0"}TEST')
    return CustomerVehicle.objects.create(customer=customer, vehicle=vehicle), customer


class StockSafetyGuardTests(TestCase):
    """AMCPackage.submit() -- must not allow a sale to go through when the
    AMC type has no stock (round-3 audit finding; the reference server
    enforces this and the Django port had silently skipped it)."""

    def setUp(self):
        self.amc_type = AMCType.objects.create(code='GOLD', name='Gold AMC')
        self.customer_vehicle, _ = _make_customer_vehicle('1')
        self.user = User.objects.create_user(username='vastest', email='vas@example.com', password='Test-Pass-123!')

    def test_submit_blocked_when_stock_is_zero(self):
        package = AMCPackage.objects.create(customer_vehicle=self.customer_vehicle, amc_type=self.amc_type)
        with self.assertRaises(ValueError):
            package.submit(self.user)
        package.refresh_from_db()
        self.assertEqual(package.docstatus, 0)

    def test_submit_succeeds_once_stock_is_available(self):
        ledger = VASStockLedger.get_or_create_for(amc_type=self.amc_type)
        VASStockLedger.objects.filter(pk=ledger.pk).update(current_stock=1)
        package = AMCPackage.objects.create(customer_vehicle=self.customer_vehicle, amc_type=self.amc_type)
        package.submit(self.user)
        package.refresh_from_db()
        self.assertEqual(package.docstatus, 1)


class AutoInvoiceTests(TestCase):
    """The post-submit signal that auto-creates a billing.Invoice from the
    package's own computed amount fields (Phase 11b)."""

    def setUp(self):
        self.amc_type = AMCType.objects.create(code='SILVER', name='Silver AMC')
        ledger = VASStockLedger.get_or_create_for(amc_type=self.amc_type)
        VASStockLedger.objects.filter(pk=ledger.pk).update(current_stock=5)
        self.user = User.objects.create_user(username='vasinv', email='vasinv@example.com', password='Test-Pass-123!')

    def test_invoice_created_when_sales_order_is_set(self):
        customer_vehicle, customer = _make_customer_vehicle('2')
        order = VehicleSalesOrder.objects.create(
            customer=customer, booking_amount=Decimal('1000'), total_amount=Decimal('100000'),
        )
        package = AMCPackage.objects.create(
            customer_vehicle=customer_vehicle, amc_type=self.amc_type, sales_order=order,
            amount=Decimal('1180'), gst_amount=Decimal('180'), without_gst_amount=Decimal('1000'),
        )
        package.submit(self.user)
        package.refresh_from_db()
        self.assertIsNotNone(package.invoice_id)
        invoice = package.invoice
        self.assertEqual(invoice.subtotal, Decimal('1000'))
        self.assertEqual(invoice.gst_amount, Decimal('180'))
        self.assertEqual(invoice.final_amount, Decimal('1180'))
        self.assertEqual(invoice.sales_order_id, order.pk)

    def test_no_invoice_created_when_sales_order_is_unset(self):
        customer_vehicle, _ = _make_customer_vehicle('3')
        package = AMCPackage.objects.create(customer_vehicle=customer_vehicle, amc_type=self.amc_type)
        package.submit(self.user)
        package.refresh_from_db()
        self.assertIsNone(package.invoice_id)


from django.test import TestCase as _TestCase
from django.urls import reverse as _reverse

from accounts.models import User as _User
from masters.models import Supplier as _Supplier
from vas.models import AMCType as _AMCType, RSAType as _RSAType, RSACreation as _RSACreation


class AMCTypeCRUDTests(_TestCase):

    def setUp(self):
        self.user = _User.objects.create_superuser(username='amctype_admin', email='amctypeadmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)

    def test_create_then_list(self):
        response = self.client.post(_reverse('vas:amc_type_create'), {
            'code': 'PLAT', 'name': 'Platinum AMC', 'amc_validity_days': '365', 'amc_amount': '2000',
        })
        self.assertEqual(response.status_code, 302)
        amc_type = _AMCType.objects.get(code='PLAT')
        self.assertEqual(amc_type.name, 'Platinum AMC')

        response = self.client.get(_reverse('vas:amc_type_list'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(amc_type, response.context['types'])


class RSACreationCRUDTests(_TestCase):

    def setUp(self):
        self.user = _User.objects.create_superuser(username='rsacre_admin', email='rsacreadmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)
        self.rsa_type = _RSAType.objects.create(code='RSA1', name='Standard RSA')
        self.supplier = _Supplier.objects.create(supplier_name='RSA Supplier Co')

    def test_create_then_submit(self):
        response = self.client.post(_reverse('vas:rsa_creation_create'), {
            'rsa_type': self.rsa_type.pk, 'rsa_amount': '500', 'supplier': self.supplier.pk,
        })
        self.assertEqual(response.status_code, 302)
        creation = _RSACreation.objects.get(rsa_type=self.rsa_type)
        self.assertEqual(creation.docstatus, 0)

        response = self.client.post(_reverse('vas:rsa_creation_submit', args=[creation.pk]))
        self.assertEqual(response.status_code, 302)
        creation.refresh_from_db()
        self.assertEqual(creation.docstatus, 1)


class VASSupplierInvoiceCreateTests(_TestCase):

    def setUp(self):
        self.user = _User.objects.create_superuser(username='vasinv_admin', email='vasinvadmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)
        self.supplier = _Supplier.objects.create(supplier_name='VAS Invoice Supplier')

    def test_create_with_no_item_rows(self):
        response = self.client.post(_reverse('vas:vas_invoice_create'), {
            'supplier': self.supplier.pk, 'invoice_date': '2020-01-01', 'payment_status': 'unpaid',
            'items-TOTAL_FORMS': '0', 'items-INITIAL_FORMS': '0',
            'items-MIN_NUM_FORMS': '0', 'items-MAX_NUM_FORMS': '1000',
        })
        self.assertEqual(response.status_code, 302)
        from vas.models import VASSupplierInvoice
        self.assertTrue(VASSupplierInvoice.objects.filter(supplier=self.supplier).exists())


class AMCPackageCreateViewTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser(username='amcview_admin', email='amcviewadmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)
        self.customer_vehicle, _ = _make_customer_vehicle('AMCVIEW1')

    def test_create(self):
        response = self.client.post(_reverse('vas:amc_create'), {
            'customer_vehicle': self.customer_vehicle.pk, 'status': 'active',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(AMCPackage.objects.filter(customer_vehicle=self.customer_vehicle).exists())

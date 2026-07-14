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

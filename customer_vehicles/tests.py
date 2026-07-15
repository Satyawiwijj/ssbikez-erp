"""
Tests for customer_vehicles -- a thin bridge app with no docstatus/ownership
logic of its own, but real cross-module aggregation in its detail view
(job cards, VAS packages, and a payment-balance computation pulled from
sales/billing) that's worth verifying directly: basic CRUD round-trip, the
list search filter, and the detail view's total_paid/balance arithmetic.
"""
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from customer_vehicles.models import CustomerVehicle
from customers.models import BikeModel, Customer, VehicleStock


def _make_customer_vehicle(suffix=''):
    customer = Customer.objects.create(full_name=f'CV Customer{suffix}', phone=f'500000000{suffix or "0"}')
    bike_model = BikeModel.objects.create(brand='Bajaj', model_name=f'Pulsar{suffix}', ex_showroom_price=Decimal('110000'))
    vehicle = VehicleStock.objects.create(bike_model=bike_model, chassis_no=f'CVCH{suffix or "0"}')
    return CustomerVehicle.objects.create(customer=customer, vehicle=vehicle, registration_no=f'KA01AB{suffix or "0"}'), customer, vehicle


class CustomerVehicleCRUDTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser(username='cv_admin', email='cvadmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)

    def test_create_then_detail_then_update_round_trip(self):
        customer = Customer.objects.create(full_name='Round Trip Customer', phone='5111111111')
        bike_model = BikeModel.objects.create(brand='Suzuki', model_name='Access', ex_showroom_price=Decimal('95000'))
        vehicle = VehicleStock.objects.create(bike_model=bike_model, chassis_no='CVROUNDTRIP1')

        response = self.client.post(reverse('customer_vehicles:customervehicle_create'), {
            'customer': customer.pk, 'vehicle': vehicle.pk, 'registration_no': 'KA05XY1234',
        })
        self.assertEqual(response.status_code, 302)
        cv = CustomerVehicle.objects.get(vehicle=vehicle)
        self.assertEqual(cv.registration_no, 'KA05XY1234')

        detail = self.client.get(reverse('customer_vehicles:customervehicle_detail', args=[cv.pk]))
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.context['cv'].pk, cv.pk)

        response = self.client.post(reverse('customer_vehicles:customervehicle_update', args=[cv.pk]), {
            'customer': customer.pk, 'vehicle': vehicle.pk, 'registration_no': 'KA05XY9999',
        })
        self.assertEqual(response.status_code, 302)
        cv.refresh_from_db()
        self.assertEqual(cv.registration_no, 'KA05XY9999')

    def test_list_search_filters_by_registration_no_and_customer_name(self):
        cv1, customer1, _ = _make_customer_vehicle('A')
        cv2, customer2, _ = _make_customer_vehicle('B')

        response = self.client.get(reverse('customer_vehicles:customervehicle_list'), {'q': customer1.full_name})
        results = list(response.context['customer_vehicles'])
        self.assertIn(cv1, results)
        self.assertNotIn(cv2, results)

        response = self.client.get(reverse('customer_vehicles:customervehicle_list'), {'q': cv2.registration_no})
        results = list(response.context['customer_vehicles'])
        self.assertIn(cv2, results)
        self.assertNotIn(cv1, results)


class CustomerVehicleDetailFinancialsTests(TestCase):
    """The detail view's total_paid/balance computation -- pulls the active
    (non-cancelled) invoice off the linked sales order and sums its
    completed payments. Real arithmetic worth checking directly, not just
    trusting the view renders without crashing."""

    def setUp(self):
        self.user = User.objects.create_superuser(username='cv_fin_admin', email='cvfinadmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)

    def test_balance_reflects_completed_payments_only(self):
        from billing.models import Invoice, Payment
        from sales.models import VehicleSalesOrder

        cv, customer, vehicle = _make_customer_vehicle('FIN')
        order = VehicleSalesOrder.objects.create(
            customer=customer, vehicle=vehicle, booking_amount=Decimal('1000'), total_amount=Decimal('110000'),
        )
        invoice = Invoice.objects.create(
            sales_order=order, invoice_number='CV-FIN-INV-1', subtotal=Decimal('110000'),
            final_amount=Decimal('110000'), invoice_date='2026-08-01',
        )
        Payment.objects.create(invoice=invoice, amount=Decimal('40000'), payment_status=Payment.PaymentStatus.COMPLETED, payment_date='2026-08-01')
        Payment.objects.create(invoice=invoice, amount=Decimal('20000'), payment_status=Payment.PaymentStatus.COMPLETED, payment_date='2026-08-02')
        # A pending payment must NOT count toward total_paid.
        Payment.objects.create(invoice=invoice, amount=Decimal('999999'), payment_status=Payment.PaymentStatus.PENDING, payment_date='2026-08-03')

        response = self.client.get(reverse('customer_vehicles:customervehicle_detail', args=[cv.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_paid'], Decimal('60000'))
        self.assertEqual(response.context['balance'], Decimal('50000'))

    def test_detail_view_handles_no_sales_order_at_all(self):
        cv, _, _ = _make_customer_vehicle('NOORDER')
        response = self.client.get(reverse('customer_vehicles:customervehicle_detail', args=[cv.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context['sales_order'])
        self.assertEqual(response.context['total_paid'], Decimal('0'))

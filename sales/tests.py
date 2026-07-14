"""
Regression tests for the highest-value sales-module bug classes found this
session: the ownership-check gaps on submit/cancel (audit rounds 1-2), the
auto-numbering race/uniqueness guarantee on order_number, and the
negative-discount business-logic gap (round 4).
"""
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import Role, User
from customers.models import BikeModel, Customer, VehicleStock
from sales.forms import VehicleSalesOrderForm
from sales.models import VehicleSalesOrder


def _make_customer(suffix=''):
    return Customer.objects.create(full_name=f'Test Customer{suffix}', phone=f'900000000{suffix or "0"}')


class OrderOwnershipTests(TestCase):
    """
    sales.views.order_submit/order_cancel must only allow the order's own
    sales_executive (or a manager) to act on it -- this was a real,
    fully-open gap on several sibling documents (e.g. fitting_create) found
    during the ownership-consistency audit rounds.
    """

    @classmethod
    def setUpTestData(cls):
        exec_role, _ = Role.objects.get_or_create(role_name='Sales Executive')
        mgr_role, _ = Role.objects.get_or_create(role_name='Sales Manager')

        cls.owner = User.objects.create_user(
            username='owner_exec', email='owner@example.com', password='Test-Pass-123!', role=exec_role,
        )
        cls.other_exec = User.objects.create_user(
            username='other_exec', email='other@example.com', password='Test-Pass-123!', role=exec_role,
        )
        cls.manager = User.objects.create_user(
            username='sales_mgr', email='mgr@example.com', password='Test-Pass-123!', role=mgr_role,
        )
        customer = _make_customer()
        cls.order = VehicleSalesOrder.objects.create(
            customer=customer, sales_executive=cls.owner,
            booking_amount=Decimal('1000'), total_amount=Decimal('100000'),
        )

    def test_non_owner_non_manager_cannot_submit(self):
        self.client.force_login(self.other_exec)
        response = self.client.post(reverse('sales:order_submit', args=[self.order.pk]))
        self.assertEqual(response.status_code, 403)
        self.order.refresh_from_db()
        self.assertEqual(self.order.docstatus, 0)

    def test_owner_can_submit(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse('sales:order_submit', args=[self.order.pk]))
        self.assertEqual(response.status_code, 302)
        self.order.refresh_from_db()
        self.assertEqual(self.order.docstatus, 1)

    def test_non_manager_cannot_cancel_even_the_owner(self):
        self.client.force_login(self.owner)
        self.client.post(reverse('sales:order_submit', args=[self.order.pk]))
        response = self.client.post(reverse('sales:order_cancel', args=[self.order.pk]))
        self.assertEqual(response.status_code, 403)

    def test_manager_can_cancel_someone_elses_order(self):
        self.client.force_login(self.owner)
        self.client.post(reverse('sales:order_submit', args=[self.order.pk]))
        self.client.force_login(self.manager)
        response = self.client.post(reverse('sales:order_cancel', args=[self.order.pk]))
        self.assertEqual(response.status_code, 302)
        self.order.refresh_from_db()
        self.assertEqual(self.order.docstatus, 2)


class OrderNumberUniquenessTests(TestCase):
    """
    VehicleSalesOrder.save()'s select_for_update()-guarded auto-numbering
    (the systemic 30-model race-condition fix from this session) must
    produce unique, sequential order_number values, never a collision.
    """

    def test_sequential_creates_get_unique_numbers(self):
        customer = _make_customer()
        orders = [
            VehicleSalesOrder.objects.create(
                customer=customer, booking_amount=Decimal('1000'), total_amount=Decimal('100000'),
            )
            for _ in range(5)
        ]
        numbers = [o.order_number for o in orders]
        self.assertEqual(len(numbers), len(set(numbers)), f"duplicate order_number values: {numbers}")
        for n in numbers:
            self.assertTrue(n.startswith('ORD-'))


class NegativeDiscountFormTests(TestCase):
    """VehicleSalesOrderForm.clean() must reject a negative discount_amount
    (round 4 finding: nothing enforced a floor, and the value feeds directly
    into the Profit Report's subtraction, inflating reported profit)."""

    def _base_payload(self, customer, **overrides):
        payload = {
            'customer': customer.pk,
            'booking_amount': '1000',
            'total_amount': '100000',
            'discount_amount': '0',
            'sales_status': VehicleSalesOrder.SalesStatus.BOOKED,
            'payment_status': VehicleSalesOrder.PaymentStatus.UNPAID,
        }
        payload.update(overrides)
        return payload

    def test_negative_discount_is_rejected(self):
        customer = _make_customer()
        form = VehicleSalesOrderForm(data=self._base_payload(customer, discount_amount='-500'))
        self.assertFalse(form.is_valid())
        self.assertIn('discount_amount', form.errors)

    def test_zero_discount_is_accepted(self):
        customer = _make_customer('2')
        form = VehicleSalesOrderForm(data=self._base_payload(customer, discount_amount='0'))
        self.assertTrue(form.is_valid(), form.errors)

    def test_positive_discount_within_bound_is_accepted(self):
        customer = _make_customer('3')
        form = VehicleSalesOrderForm(data=self._base_payload(customer, discount_amount='5000'))
        self.assertTrue(form.is_valid(), form.errors)

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


def _formset_management_form(prefix, total=0):
    return {
        f'{prefix}-TOTAL_FORMS': str(total),
        f'{prefix}-INITIAL_FORMS': '0',
        f'{prefix}-MIN_NUM_FORMS': '0',
        f'{prefix}-MAX_NUM_FORMS': '1000',
    }


class SalesEnquiryCRUDTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser(username='enq_admin', email='enqadmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)

    def _payload(self, customer, **overrides):
        payload = {'customer': customer.pk, 'status': 'open'}
        payload.update(_formset_management_form('calllogs'))
        payload.update(_formset_management_form('histories'))
        payload.update(overrides)
        return payload

    def test_create_then_detail_then_update_round_trip(self):
        customer = _make_customer('ENQ1')
        response = self.client.post(reverse('sales:enquiry_create'), self._payload(customer))
        self.assertEqual(response.status_code, 302, )
        from sales.models import SalesEnquiry
        enquiry = SalesEnquiry.objects.get(customer=customer)
        self.assertEqual(enquiry.sales_executive_id, self.user.pk)  # auto-assigned when unset

        response = self.client.get(reverse('sales:enquiry_detail', args=[enquiry.pk]))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse('sales:enquiry_list'))
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            reverse('sales:enquiry_update', args=[enquiry.pk]),
            self._payload(customer, status='follow_up'),
        )
        self.assertEqual(response.status_code, 302)
        enquiry.refresh_from_db()
        self.assertEqual(enquiry.status, 'follow_up')

    def test_create_without_customer_or_prospect_is_rejected(self):
        payload = {**_formset_management_form('calllogs'), **_formset_management_form('histories')}
        response = self.client.post(reverse('sales:enquiry_create'), payload)
        self.assertEqual(response.status_code, 200)
        from sales.models import SalesEnquiry
        self.assertEqual(SalesEnquiry.objects.count(), 0)


class DealerCRUDTests(TestCase):
    """The Dealer master (Phase 13 wholesale-resale sub-module) -- a plain,
    non-submittable CRUD screen with no formset."""

    def setUp(self):
        self.user = User.objects.create_superuser(username='dealer_admin', email='dealeradmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)
        from accounts.models import Branch
        from masters.models import Warehouse
        self.branch = Branch.objects.create(branch_name='Dealer Branch')
        self.warehouse = Warehouse.objects.create(name='Dealer Warehouse')

    def test_create_list_detail_round_trip(self):
        response = self.client.post(reverse('sales:dealer_create'), {
            'dealer_name': 'Wholesale Partner A', 'mobile_number': '9800000001',
            'warehouse': self.warehouse.pk, 'branch': self.branch.pk,
        })
        self.assertEqual(response.status_code, 302)
        from sales.models import Dealer
        dealer = Dealer.objects.get(dealer_name='Wholesale Partner A')

        response = self.client.get(reverse('sales:dealer_list'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(dealer, response.context['dealers'])

        response = self.client.get(reverse('sales:dealer_detail', args=[dealer.pk]))
        self.assertEqual(response.status_code, 200)


class SalesTargetCRUDTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser(username='target_admin', email='targetadmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)

    def test_create_then_list(self):
        response = self.client.post(reverse('sales:target_create'), {
            'sales_executive': self.user.pk, 'month': '8', 'year': '2026',
            'target_enquiries': '20', 'target_test_rides': '10', 'target_conversions': '5', 'target_revenue': '500000',
        })
        self.assertEqual(response.status_code, 302)
        from sales.models import SalesTarget
        self.assertTrue(SalesTarget.objects.filter(sales_executive=self.user, month=8, year=2026).exists())
        response = self.client.get(reverse('sales:target_list'))
        self.assertEqual(response.status_code, 200)


class ExchangeVehicleDealerCRUDTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser(username='evd_admin', email='evdadmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)
        from masters.models import Warehouse
        from sales.models import Dealer
        from accounts.models import Branch
        self.from_wh = Warehouse.objects.create(name='EVD From WH')
        self.to_wh = Warehouse.objects.create(name='EVD To WH')
        self.branch = Branch.objects.create(branch_name='EVD Branch')
        self.dealer = Dealer.objects.create(
            dealer_name='EVD Dealer', mobile_number='9500000001', warehouse=self.to_wh, branch=self.branch,
        )

    def test_create_with_no_item_rows_then_detail(self):
        response = self.client.post(reverse('sales:exchange_vehicle_dealer_create'), {
            'date': '2026-08-01', 'from_warehouse': self.from_wh.pk, 'to_warehouse': self.to_wh.pk,
            'dealer': self.dealer.pk, 'branch': self.branch.pk,
            'items-TOTAL_FORMS': '0', 'items-INITIAL_FORMS': '0',
            'items-MIN_NUM_FORMS': '0', 'items-MAX_NUM_FORMS': '1000',
        })
        self.assertEqual(response.status_code, 302)
        from sales.models import ExchangeVehicleDealer
        transfer = ExchangeVehicleDealer.objects.get(dealer=self.dealer)
        response = self.client.get(reverse('sales:exchange_vehicle_dealer_detail', args=[transfer.pk]))
        self.assertEqual(response.status_code, 200)


class DeliveryCreateTests(TestCase):

    def setUp(self):
        exec_role, _ = Role.objects.get_or_create(role_name='Sales Executive')
        self.owner = User.objects.create_user(username='del_owner', email='delowner@example.com', password='Test-Pass-123!', role=exec_role)
        self.other = User.objects.create_user(username='del_other', email='delother@example.com', password='Test-Pass-123!', role=exec_role)
        customer = _make_customer('DEL1')
        self.order = VehicleSalesOrder.objects.create(
            customer=customer, sales_executive=self.owner, booking_amount=Decimal('1000'), total_amount=Decimal('100000'),
        )
        # Delivery can only be created against a Submitted order (fixed to reject
        # Draft orders in the same session this test predates).
        self.order.submit(self.owner)

    def _payload(self, **overrides):
        payload = {
            'sales_order': self.order.pk, 'delivery_date': '2020-01-01', 'total_amount': '50000', 'payment_status': 'unpaid',
        }
        payload.update(_formset_management_form('delivery_items'))
        payload.update(_formset_management_form('delivery_advance'))
        payload.update(_formset_management_form('delivery_payments'))
        payload.update(overrides)
        return payload

    def test_owner_can_create_delivery(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse('sales:delivery_create'), self._payload())
        self.assertEqual(response.status_code, 302)
        from sales.models import VehicleDelivery
        self.assertTrue(VehicleDelivery.objects.filter(sales_order=self.order).exists())

    def test_non_owner_cannot_create_delivery_for_someone_elses_order(self):
        self.client.force_login(self.other)
        response = self.client.post(reverse('sales:delivery_create'), self._payload())
        self.assertEqual(response.status_code, 403)


class AppointmentCreateTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser(username='apt_admin', email='aptadmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)
        customer = _make_customer('APT1')
        from sales.models import SalesEnquiry
        self.enquiry = SalesEnquiry.objects.create(customer=customer)

    def test_create(self):
        from django.utils import timezone
        import datetime
        future = (timezone.now() + datetime.timedelta(days=1)).strftime('%Y-%m-%dT%H:%M')
        response = self.client.post(reverse('sales:appointment_create'), {
            'enquiry': self.enquiry.pk, 'appointment_date': future, 'status': 'scheduled',
        })
        self.assertEqual(response.status_code, 302)
        from sales.models import SalesAppointment
        self.assertTrue(SalesAppointment.objects.filter(enquiry=self.enquiry).exists())


class ExchangeVehicleCreateTests(TestCase):

    def setUp(self):
        exec_role, _ = Role.objects.get_or_create(role_name='Sales Executive')
        self.owner = User.objects.create_user(username='exch_owner', email='exchowner@example.com', password='Test-Pass-123!', role=exec_role)
        customer = _make_customer('EXCH1')
        self.order = VehicleSalesOrder.objects.create(
            customer=customer, sales_executive=self.owner, booking_amount=Decimal('1000'), total_amount=Decimal('100000'),
        )

    def test_owner_can_create_exchange(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse('sales:exchange_create'), {
            'sales_order': self.order.pk, 'old_vehicle_model': 'Honda Activa', 'registration_no': 'KA01EX0001',
            'valuation_amount': '30000', 'payment_status': 'pending',
        })
        self.assertEqual(response.status_code, 302)
        from sales.models import ExchangeVehicle
        self.assertTrue(ExchangeVehicle.objects.filter(sales_order=self.order).exists())


class OrderAmendTests(TestCase):

    def setUp(self):
        exec_role, _ = Role.objects.get_or_create(role_name='Sales Executive')
        mgr_role, _ = Role.objects.get_or_create(role_name='Sales Manager')
        self.owner = User.objects.create_user(username='amend_owner', email='amendowner@example.com', password='Test-Pass-123!', role=exec_role)
        self.manager = User.objects.create_user(username='amend_mgr', email='amendmgr@example.com', password='Test-Pass-123!', role=mgr_role)
        customer = _make_customer('AMEND1')
        self.order = VehicleSalesOrder.objects.create(
            customer=customer, sales_executive=self.owner, booking_amount=Decimal('1000'), total_amount=Decimal('100000'),
        )
        self.order.submit(self.owner)
        self.order.cancel(self.manager)

    def test_amend_creates_new_linked_draft(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse('sales:order_amend', args=[self.order.pk]))
        self.assertEqual(response.status_code, 302)
        from sales.models import VehicleSalesOrder as VSO
        amended = VSO.objects.filter(amended_from=self.order).first()
        self.assertIsNotNone(amended)
        self.assertEqual(amended.docstatus, 0)
        self.assertNotEqual(amended.order_number, self.order.order_number)


class EnquiryChildAddTests(TestCase):
    """calllog_add/history_add -- standalone side doors onto SalesEnquiry,
    both ownership-gated the same way enquiry_update itself is."""

    def setUp(self):
        exec_role, _ = Role.objects.get_or_create(role_name='Sales Executive')
        self.owner = User.objects.create_user(username='cl_owner', email='clowner@example.com', password='Test-Pass-123!', role=exec_role)
        self.other = User.objects.create_user(username='cl_other', email='clother@example.com', password='Test-Pass-123!', role=exec_role)
        customer = _make_customer('CLOG1')
        from sales.models import SalesEnquiry
        self.enquiry = SalesEnquiry.objects.create(customer=customer, sales_executive=self.owner)

    def test_owner_can_add_calllog(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse('sales:calllog_add', args=[self.enquiry.pk]), {'bill_sec': '30'})
        self.assertEqual(response.status_code, 302)

    def test_other_cannot_add_calllog(self):
        self.client.force_login(self.other)
        response = self.client.post(reverse('sales:calllog_add', args=[self.enquiry.pk]), {'bill_sec': '30'})
        self.assertEqual(response.status_code, 403)

    def test_owner_can_add_history(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse('sales:history_add', args=[self.enquiry.pk]), {
            'update_date': '2020-01-01', 'remarks': 'Followed up', 'status': 'Open',
        })
        self.assertEqual(response.status_code, 302)


class FeedbackCreateTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser(username='fb_admin', email='fbadmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)
        customer = _make_customer('FB1')
        from sales.models import SalesEnquiry
        self.enquiry = SalesEnquiry.objects.create(customer=customer)

    def test_create_with_no_item_rows(self):
        payload = {'enquiry': self.enquiry.pk}
        payload.update(_formset_management_form('feedback_items'))
        response = self.client.post(reverse('sales:feedback_create'), payload)
        self.assertEqual(response.status_code, 302)
        from sales.models import SalesFeedback
        self.assertTrue(SalesFeedback.objects.filter(enquiry=self.enquiry).exists())


class SalesOrderTotalRecomputeTests(TestCase):

    def setUp(self):
        from customers.models import Customer
        self.customer = Customer.objects.create(full_name='Order Total Customer', phone='9000000020')

    def test_total_amount_reflects_summed_line_items_after_create(self):
        from django.test import Client
        from django.urls import reverse
        from accounts.models import User

        user = User.objects.create_superuser(username='order_total_admin', email='ordertotal@example.com', password='Test-Pass-123!')
        client = Client()
        client.force_login(user)

        response = client.post(reverse('sales:order_create'), {
            'customer': self.customer.pk, 'booking_amount': '1000', 'discount_amount': '0',
            'sales_status': VehicleSalesOrder.SalesStatus.BOOKED,
            'payment_status': VehicleSalesOrder.PaymentStatus.UNPAID,
            'items-TOTAL_FORMS': '2', 'items-INITIAL_FORMS': '0',
            'items-MIN_NUM_FORMS': '0', 'items-MAX_NUM_FORMS': '1000',
            'items-0-item_name': 'Helmet', 'items-0-rate': '500', 'items-0-quantity': '1', 'items-0-amount': '500',
            'items-1-item_name': 'Accessories', 'items-1-rate': '300', 'items-1-quantity': '2', 'items-1-amount': '600',
            'additional_fittings-TOTAL_FORMS': '0', 'additional_fittings-INITIAL_FORMS': '0',
            'additional_fittings-MIN_NUM_FORMS': '0', 'additional_fittings-MAX_NUM_FORMS': '1000',
            'advance_payments-TOTAL_FORMS': '0', 'advance_payments-INITIAL_FORMS': '0',
            'advance_payments-MIN_NUM_FORMS': '0', 'advance_payments-MAX_NUM_FORMS': '1000',
        })
        self.assertEqual(response.status_code, 302)

        order = VehicleSalesOrder.objects.get(customer=self.customer)
        self.assertEqual(order.total_amount, Decimal('1100'))


class VehicleDeliveryTotalRecomputeTests(TestCase):

    def test_total_amount_reflects_summed_delivery_items(self):
        from customers.models import Customer
        from sales.models import VehicleDelivery, DeliveryNoteItem

        customer = Customer.objects.create(full_name='Delivery Total Customer', phone='9000000030')
        order = VehicleSalesOrder.objects.create(customer=customer, booking_amount=Decimal('1000'), total_amount=Decimal('50000'))
        delivery = VehicleDelivery.objects.create(sales_order=order, delivery_date='2026-08-01', total_amount=Decimal('0'))
        DeliveryNoteItem.objects.create(delivery=delivery, item_code='HELMET', rate=Decimal('500'), actual_amount=Decimal('500'))
        DeliveryNoteItem.objects.create(delivery=delivery, item_code='ACCESSORY-KIT', rate=Decimal('750'), actual_amount=Decimal('750'))

        delivery.recompute_totals()

        delivery.refresh_from_db()
        self.assertEqual(delivery.total_amount, Decimal('1250'))

    def test_total_amount_reflects_summed_delivery_items_after_create_view(self):
        from django.test import Client
        from accounts.models import User
        from customers.models import Customer
        from sales.models import VehicleDelivery

        customer = Customer.objects.create(full_name='Delivery Total View Customer', phone='9000000031')
        order = VehicleSalesOrder.objects.create(
            customer=customer, booking_amount=Decimal('1000'), total_amount=Decimal('50000'),
            docstatus=VehicleSalesOrder.DocStatus.SUBMITTED,
        )

        user = User.objects.create_superuser(username='delivery_total_admin', email='deliverytotal@example.com', password='Test-Pass-123!')
        client = Client()
        client.force_login(user)

        payload = {
            'sales_order': order.pk, 'delivery_date': '2026-08-01',
            'payment_status': VehicleDelivery.PaymentStatus.UNPAID,
        }
        payload.update(_formset_management_form('delivery_items', total=2))
        payload.update({
            'delivery_items-0-item_code': 'HELMET', 'delivery_items-0-warranty_rsa_amc': 'none',
            'delivery_items-0-rate': '500', 'delivery_items-0-actual_amount': '500',
            'delivery_items-1-item_code': 'ACCESSORY-KIT', 'delivery_items-1-warranty_rsa_amc': 'none',
            'delivery_items-1-rate': '750', 'delivery_items-1-actual_amount': '750',
        })
        payload.update(_formset_management_form('delivery_advance'))
        payload.update(_formset_management_form('delivery_payments'))

        response = client.post(reverse('sales:delivery_create'), payload)
        self.assertEqual(response.status_code, 302)

        delivery = VehicleDelivery.objects.get(sales_order=order)
        self.assertEqual(delivery.total_amount, Decimal('1250'))

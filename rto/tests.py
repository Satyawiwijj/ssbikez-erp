"""
Regression tests for the RTO module's real, live-caught bug (a 500 on every
RTO Registration detail page after Phase 9a restructured RTOPayment/
RegpayCreation into header+item batch documents, since the view still
queried the old header-level field names) plus the batch-total computation
those same restructured models depend on.
"""
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from customers.models import BikeModel, Customer
from rto.models import (RegPayBaseAmount, RegpayCreation, RegpayCreationItem,
                         RTOPayment, RTOPaymentItem, RTORegistration)
from sales.models import VehicleSalesOrder


def _make_order(suffix=''):
    customer = Customer.objects.create(full_name=f'RTO Customer{suffix}', phone=f'700000000{suffix or "0"}')
    return VehicleSalesOrder.objects.create(
        customer=customer, booking_amount=Decimal('1000'), total_amount=Decimal('100000'),
    )


class RegistrationDetailRegressionTests(TestCase):
    """The exact bug: rto.views.registration_detail queried
    order.rto_payments/order.regpay_creations (stale, pre-Phase-9a field
    names) after those FKs moved onto the item child rows. Fixed by querying
    RTOPayment/RegpayCreation via items__sales_order=order. This must not
    regress -- every RTO Registration detail page 500'd before the fix."""

    def setUp(self):
        self.user = User.objects.create_superuser(
            username='rto_admin', email='rtoadmin@example.com', password='Test-Pass-123!',
        )
        self.order = _make_order('1')
        self.registration = RTORegistration.objects.create(sales_order=self.order)

    def test_detail_page_loads_with_no_linked_payments(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('rto:registration_detail', args=[self.registration.pk]))
        self.assertEqual(response.status_code, 200)

    def test_detail_page_correctly_surfaces_linked_batch_payment(self):
        payment = RTOPayment.objects.create(direction=RTOPayment.Direction.INCOME)
        RTOPaymentItem.objects.create(payment=payment, sales_order=self.order, flag_amount=Decimal('500'))
        # A second, unrelated order/payment must NOT leak into this registration's page.
        other_order = _make_order('2')
        other_payment = RTOPayment.objects.create(direction=RTOPayment.Direction.INCOME)
        RTOPaymentItem.objects.create(payment=other_payment, sales_order=other_order, flag_amount=Decimal('999'))

        self.client.force_login(self.user)
        response = self.client.get(reverse('rto:registration_detail', args=[self.registration.pk]))
        self.assertEqual(response.status_code, 200)
        rto_payments = list(response.context['rto_payments'])
        self.assertIn(payment, rto_payments)
        self.assertNotIn(other_payment, rto_payments)

    def test_detail_page_correctly_surfaces_linked_regpay_creation(self):
        bike_model = BikeModel.objects.create(brand='Honda', model_name='Activa', ex_showroom_price=Decimal('80000'))
        base_amount = RegPayBaseAmount.objects.create(vehicle=bike_model, amount=Decimal('300'))
        regpay = RegpayCreation.objects.create()
        RegpayCreationItem.objects.create(regpay=regpay, sales_order=self.order, vehicle_type=base_amount)

        self.client.force_login(self.user)
        response = self.client.get(reverse('rto:registration_detail', args=[self.registration.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertIn(regpay, list(response.context['regpay_creations']))


class BatchItemTotalComputationTests(TestCase):
    """RTOPaymentItem.save() computes its own row total -- the header's
    total_amount is a separate rollup computed in the view after formset
    save, this only covers the row-level piece that's a real model method."""

    def test_rto_payment_item_total_sums_its_three_amount_fields(self):
        order = _make_order('3')
        payment = RTOPayment.objects.create(direction=RTOPayment.Direction.EXPENSE)
        item = RTOPaymentItem.objects.create(
            payment=payment, sales_order=order,
            flag_amount=Decimal('100'), fine_amount=Decimal('50'), license_amount=Decimal('25'),
        )
        self.assertEqual(item.total_amount, Decimal('175'))


from django.test import TestCase as _TestCase
from django.urls import reverse as _reverse

from accounts.models import User as _User
from rto.models import RCHandOver as _RCHandOver


class RCHandOverCRUDTests(_TestCase):

    def setUp(self):
        self.user = _User.objects.create_superuser(username='rch_admin', email='rchadmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)
        self.order = _make_order('RCH1')

    def test_create_then_detail_then_submit(self):
        response = self.client.post(_reverse('rto:rc_hand_over_create'), {
            'sales_order': self.order.pk, 'rc_book_received': 'yes', 'rc_book_number': 'RCB-0001',
        })
        self.assertEqual(response.status_code, 302)
        handover = _RCHandOver.objects.get(sales_order=self.order)

        response = self.client.get(_reverse('rto:rc_hand_over_detail', args=[handover.pk]))
        self.assertEqual(response.status_code, 200)

        response = self.client.post(_reverse('rto:rc_hand_over_submit', args=[handover.pk]))
        self.assertEqual(response.status_code, 302)
        handover.refresh_from_db()
        self.assertEqual(handover.docstatus, 1)

    def test_rc_book_received_yes_requires_rc_book_number(self):
        from rto.forms import RCHandOverForm
        form = RCHandOverForm(data={'sales_order': self.order.pk, 'rc_book_received': 'yes', 'rc_book_number': ''})
        self.assertFalse(form.is_valid())


from rto.models import Form20Creation as _Form20Creation


class Form20CreationCRUDTests(_TestCase):

    def setUp(self):
        self.user = _User.objects.create_superuser(username='f20_admin', email='f20admin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)
        self.order = _make_order('F20-1')

    def test_create_then_detail(self):
        response = self.client.post(_reverse('rto:form20_creation_create'), {
            'sales_order': self.order.pk, 'engine_no': 'ENF20001', 'frame_no': 'FRF20001', 'application_no': 'APP-0001',
        })
        self.assertEqual(response.status_code, 302)
        f20 = _Form20Creation.objects.get(sales_order=self.order)
        response = self.client.get(_reverse('rto:form20_creation_detail', args=[f20.pk]))
        self.assertEqual(response.status_code, 200)


from rto.models import RCBookCreation as _RCBookCreation, RegistrationNoCreation as _RegistrationNoCreation


class RegistrationNoCreationCRUDTests(_TestCase):

    def setUp(self):
        self.user = _User.objects.create_superuser(username='regno_admin', email='regnoadmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)
        self.order = _make_order('REGNO1')

    def test_create(self):
        response = self.client.post(_reverse('rto:registration_no_creation_create'), {
            'sales_order': self.order.pk, 'reg_no': 'KA05REG0001', 'status': 'open',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(_RegistrationNoCreation.objects.filter(sales_order=self.order).exists())


class RCBookCreationCRUDTests(_TestCase):

    def setUp(self):
        self.user = _User.objects.create_superuser(username='rcbook_admin', email='rcbookadmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)
        self.order = _make_order('RCBK1')
        self.registration = RTORegistration.objects.create(sales_order=self.order)

    def test_create(self):
        response = self.client.post(_reverse('rto:rc_book_creation_create'), {
            'rto_registration': self.registration.pk,
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(_RCBookCreation.objects.filter(rto_registration=self.registration).exists())

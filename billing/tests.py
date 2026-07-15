"""
Regression tests for the negative-discount validator gap found in round 4
of the audit: several discount fields fed directly into a real financial
subtraction with no lower bound, so a negative value would silently
*increase* a computed total/profit figure instead of being rejected.

These test the model field's own validators in isolation (not a full
object graph) since the defect and the fix are both at the field level.
"""
from django.core.exceptions import ValidationError
from django.test import TestCase

from billing.models import Invoice, InvoiceItem


class NegativeDiscountValidatorTests(TestCase):

    def test_invoiceitem_discount_rejects_negative(self):
        field = InvoiceItem._meta.get_field('discount')
        with self.assertRaises(ValidationError):
            field.clean(-10, None)

    def test_invoiceitem_discount_accepts_zero_and_positive(self):
        field = InvoiceItem._meta.get_field('discount')
        field.clean(0, None)
        field.clean(50, None)

    def test_invoice_discount_amount_rejects_negative(self):
        field = Invoice._meta.get_field('discount_amount')
        with self.assertRaises(ValidationError):
            field.clean(-1, None)

    def test_invoice_delivery_discount_rejects_negative(self):
        field = Invoice._meta.get_field('delivery_discount')
        with self.assertRaises(ValidationError):
            field.clean(-1, None)

    def test_invoice_sales_order_discount_amount_rejects_negative(self):
        field = Invoice._meta.get_field('sales_order_discount_amount')
        with self.assertRaises(ValidationError):
            field.clean(-1, None)


from decimal import Decimal as _Decimal

from django.test import TestCase as _TestCase
from django.urls import reverse as _reverse

from accounts.models import User as _User
from customers.models import Customer as _Customer
from sales.models import VehicleSalesOrder as _VehicleSalesOrder


def _make_order(suffix=''):
    customer = _Customer.objects.create(full_name=f'Billing Customer{suffix}', phone=f'400000000{suffix or "0"}')
    return _VehicleSalesOrder.objects.create(
        customer=customer, booking_amount=_Decimal('1000'), total_amount=_Decimal('100000'),
    )


class InsurancePolicyCRUDTests(_TestCase):

    def setUp(self):
        self.user = _User.objects.create_superuser(username='ins_admin', email='insadmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)

    def test_create_detail_update_round_trip(self):
        order = _make_order('IP1')
        response = self.client.post(_reverse('billing:insurance_policy_create'), {
            'sales_order': order.pk, 'provider_name': 'ICICI Lombard', 'policy_number': 'POL-0001',
            'premium_amount': '3500', 'start_date': '2026-08-01', 'end_date': '2027-08-01',
        })
        self.assertEqual(response.status_code, 302)
        from billing.models import InsurancePolicy
        policy = InsurancePolicy.objects.get(policy_number='POL-0001')

        response = self.client.get(_reverse('billing:insurance_policy_detail', args=[policy.pk]))
        self.assertEqual(response.status_code, 200)

        response = self.client.post(_reverse('billing:insurance_policy_update', args=[policy.pk]), {
            'sales_order': order.pk, 'provider_name': 'ICICI Lombard', 'policy_number': 'POL-0001',
            'premium_amount': '4000', 'start_date': '2026-08-01', 'end_date': '2027-08-01',
        })
        self.assertEqual(response.status_code, 302)
        policy.refresh_from_db()
        self.assertEqual(policy.premium_amount, _Decimal('4000'))


class FinanceLoanCRUDTests(_TestCase):

    def setUp(self):
        self.user = _User.objects.create_superuser(username='loan_admin', email='loanadmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)

    def test_create_detail_update_round_trip(self):
        order = _make_order('LN1')
        response = self.client.post(_reverse('billing:loan_create'), {
            'sales_order': order.pk, 'bank_name': 'HDFC Bank', 'loan_amount': '60000',
            'loan_status': 'active', 'hp_status': 'not_applicable',
        })
        self.assertEqual(response.status_code, 302)
        from billing.models import FinanceLoan
        loan = FinanceLoan.objects.get(sales_order=order)

        response = self.client.get(_reverse('billing:loan_detail', args=[loan.pk]))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(_reverse('billing:loan_list'))
        self.assertEqual(response.status_code, 200)

        response = self.client.post(_reverse('billing:loan_update', args=[loan.pk]), {
            'sales_order': order.pk, 'bank_name': 'HDFC Bank', 'loan_amount': '65000',
            'loan_status': 'closed', 'hp_status': 'not_applicable',
        })
        self.assertEqual(response.status_code, 302)
        loan.refresh_from_db()
        self.assertEqual(loan.loan_status, 'closed')


class InvoiceLifecycleCRUDTests(_TestCase):
    """Invoice create (auto GST calc) -> MD approval gate -> submit,
    covering the real create view rather than direct model construction."""

    def setUp(self):
        self.user = _User.objects.create_superuser(username='inv_admin', email='invadmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)

    def test_invoice_create_computes_gst_from_subtotal(self):
        order = _make_order('INV1')
        response = self.client.post(_reverse('billing:invoice_create'), {
            'sales_order': order.pk, 'invoice_number': 'BILL-INV-0001', 'subtotal': '100000', 'discount_amount': '0',
            'invoice_date': '2026-08-01', 'status': 'unpaid',
            'items-TOTAL_FORMS': '0', 'items-INITIAL_FORMS': '0',
            'items-MIN_NUM_FORMS': '0', 'items-MAX_NUM_FORMS': '1000',
        })
        self.assertEqual(response.status_code, 302)
        from billing.models import Invoice
        invoice = Invoice.objects.get(invoice_number='BILL-INV-0001')
        self.assertGreater(invoice.gst_amount, 0)
        self.assertEqual(invoice.final_amount, invoice.subtotal + invoice.gst_amount - invoice.discount_amount)


class PaymentCRUDTests(_TestCase):

    def setUp(self):
        self.user = _User.objects.create_superuser(username='pay_admin', email='payadmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)
        from billing.models import Invoice
        order = _make_order('PAY1')
        self.invoice = Invoice.objects.create(
            sales_order=order, invoice_number='PAY-INV-0001', subtotal=_Decimal('50000'),
            final_amount=_Decimal('50000'), invoice_date='2026-08-01',
        )

    def test_create_payment(self):
        response = self.client.post(_reverse('billing:payment_create'), {
            'invoice': self.invoice.pk, 'amount': '20000', 'payment_status': 'completed', 'payment_date': '2020-01-01',
        })
        self.assertEqual(response.status_code, 302)
        from billing.models import Payment
        self.assertTrue(Payment.objects.filter(invoice=self.invoice, amount=_Decimal('20000')).exists())


class JournalEntryCreateTests(_TestCase):

    def setUp(self):
        self.user = _User.objects.create_superuser(username='je_admin', email='jeadmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)

    def test_create_balanced_entry(self):
        payload = {
            'entry_date': '2020-01-01', 'description': 'Test balanced entry',
            'lines-TOTAL_FORMS': '2', 'lines-INITIAL_FORMS': '0',
            'lines-MIN_NUM_FORMS': '0', 'lines-MAX_NUM_FORMS': '1000',
            'lines-0-account': 'Cash', 'lines-0-debit': '1000', 'lines-0-credit': '0',
            'lines-1-account': 'Sales', 'lines-1-debit': '0', 'lines-1-credit': '1000',
        }
        response = self.client.post(_reverse('billing:journal_entry_create'), payload)
        self.assertEqual(response.status_code, 302)
        from billing.models import JournalEntry
        self.assertTrue(JournalEntry.objects.filter(description='Test balanced entry').exists())

    def test_unbalanced_entry_is_rejected(self):
        payload = {
            'entry_date': '2020-01-01', 'description': 'Unbalanced entry',
            'lines-TOTAL_FORMS': '2', 'lines-INITIAL_FORMS': '0',
            'lines-MIN_NUM_FORMS': '0', 'lines-MAX_NUM_FORMS': '1000',
            'lines-0-account': 'Cash', 'lines-0-debit': '1000', 'lines-0-credit': '0',
            'lines-1-account': 'Sales', 'lines-1-debit': '0', 'lines-1-credit': '500',
        }
        response = self.client.post(_reverse('billing:journal_entry_create'), payload)
        self.assertEqual(response.status_code, 200)
        from billing.models import JournalEntry
        self.assertFalse(JournalEntry.objects.filter(description='Unbalanced entry').exists())

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
        # subtotal is posted as '0' (not '100000') because Invoice.recompute_totals()
        # now derives subtotal from the InvoiceItem line items after the items
        # formset saves -- a posted subtotal is no longer authoritative. This test
        # previously posted subtotal=100000 with zero line items and asserted it
        # survived untouched, which was asserting the pre-fix bug (client report:
        # "Invoice calculation is not working during invoice creation").
        order = _make_order('INV1')
        response = self.client.post(_reverse('billing:invoice_create'), {
            'sales_order': order.pk, 'invoice_number': 'BILL-INV-0001', 'subtotal': '0', 'discount_amount': '0',
            'invoice_date': '2026-08-01', 'status': 'unpaid',
            'items-TOTAL_FORMS': '1', 'items-INITIAL_FORMS': '0',
            'items-MIN_NUM_FORMS': '0', 'items-MAX_NUM_FORMS': '1000',
            'items-0-item_code': 'FULL-KIT', 'items-0-rate': '100000', 'items-0-discount': '0', 'items-0-total': '100000',
        })
        self.assertEqual(response.status_code, 302)
        from billing.models import Invoice
        invoice = Invoice.objects.get(invoice_number='BILL-INV-0001')
        self.assertEqual(invoice.subtotal, _Decimal('100000'))
        self.assertGreater(invoice.gst_amount, 0)
        self.assertEqual(invoice.final_amount, invoice.subtotal + invoice.gst_amount - invoice.discount_amount)


class InvoiceSubtotalRecomputeTests(_TestCase):

    def setUp(self):
        self.user = _User.objects.create_superuser(username='inv_recalc_admin', email='invrecalc@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)

    def test_subtotal_reflects_summed_line_items_after_create(self):
        order = _make_order('INVRECALC1')
        response = self.client.post(_reverse('billing:invoice_create'), {
            'sales_order': order.pk, 'invoice_number': 'RECALC-INV-0001',
            'subtotal': '0', 'discount_amount': '0',
            'invoice_date': '2026-08-01', 'status': 'unpaid',
            'items-TOTAL_FORMS': '2', 'items-INITIAL_FORMS': '0',
            'items-MIN_NUM_FORMS': '0', 'items-MAX_NUM_FORMS': '1000',
            'items-0-item_code': 'ENGINE-OIL', 'items-0-rate': '400', 'items-0-discount': '0', 'items-0-total': '400',
            'items-1-item_code': 'BRAKE-PAD', 'items-1-rate': '600', 'items-1-discount': '0', 'items-1-total': '600',
        })
        self.assertEqual(response.status_code, 302)
        from billing.models import Invoice
        invoice = Invoice.objects.get(invoice_number='RECALC-INV-0001')
        self.assertEqual(invoice.subtotal, _Decimal('1000'))
        self.assertEqual(invoice.final_amount, invoice.subtotal + invoice.gst_amount)


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


class InvoiceCancelReversesJournalEntryTests(_TestCase):

    def setUp(self):
        self.user = _User.objects.create_superuser(
            username='cancel_admin', email='canceladmin@example.com', password='Test-Pass-123!'
        )
        from billing.models import Invoice
        order = _make_order('CANCELJE1')
        self.invoice = Invoice.objects.create(
            sales_order=order, invoice_number='CANCEL-INV-0001',
            subtotal=_Decimal('50000'), final_amount=_Decimal('50000'),
            invoice_date='2026-08-01',
        )

    def test_cancel_posts_a_reversing_journal_entry(self):
        self.invoice.submit(self.user)
        original_entry = self.invoice.journal_entry
        self.assertEqual(original_entry.total_debit, _Decimal('50000.00'))

        self.invoice.cancel(self.user)

        from billing.models import JournalEntry
        reversal = JournalEntry.objects.filter(
            reference_doctype='billing.Invoice',
            reference_docname=str(self.invoice.pk),
        ).exclude(pk=original_entry.pk).first()
        self.assertIsNotNone(reversal, 'Expected a reversing JournalEntry after cancel')
        self.assertEqual(reversal.lines.get(account='Accounts Receivable').credit, _Decimal('50000.00'))
        self.assertEqual(reversal.lines.get(account='Sales Revenue').debit, _Decimal('50000.00'))

    def test_cancel_twice_does_not_double_reverse(self):
        self.invoice.submit(self.user)
        self.invoice.cancel(self.user)
        from billing.models import JournalEntry
        count_after_first_cancel = JournalEntry.objects.filter(
            reference_doctype='billing.Invoice', reference_docname=str(self.invoice.pk),
        ).count()
        with self.assertRaises(ValueError):
            self.invoice.cancel(self.user)  # DocStatusMixin.cancel already guards non-Submitted state
        count_after_second_attempt = JournalEntry.objects.filter(
            reference_doctype='billing.Invoice', reference_docname=str(self.invoice.pk),
        ).count()
        self.assertEqual(count_after_first_cancel, count_after_second_attempt)


class PaymentReconciliationPostsJournalEntryTests(_TestCase):
    """GAP found during Tier 2 (Billing/GL) parity audit: a Payment created
    Pending and later reconciled to Completed via the bulk payment_reconciliation
    view never posted its Dr Cash-or-Bank / Cr Accounts Receivable JournalEntry,
    because Payment.save() only auto-posted for a *newly created* already-Completed
    Payment (`is_new and status == COMPLETED`), and the reconciliation view used
    QuerySet.update() which bypasses save() entirely -- so neither path could ever
    fire the GL hook for a Pending -> Completed transition. Same class of bug as
    the Invoice.cancel() GL-reversal gap fixed earlier in this audit: a payment
    the UI shows as "Completed" with no corresponding General Ledger entry."""

    def setUp(self):
        self.user = _User.objects.create_superuser(
            username='recon_admin', email='reconadmin@example.com', password='Test-Pass-123!'
        )
        self.client.force_login(self.user)
        from billing.models import Invoice
        order = _make_order('RECON1')
        self.invoice = Invoice.objects.create(
            sales_order=order, invoice_number='RECON-INV-0001', subtotal=_Decimal('30000'),
            final_amount=_Decimal('30000'), invoice_date='2026-08-01',
        )

    def test_reconciling_a_pending_payment_posts_journal_entry(self):
        from billing.models import Payment
        payment = Payment.objects.create(
            invoice=self.invoice, amount=_Decimal('30000'),
            payment_method=Payment.Method.CASH,
            payment_status=Payment.PaymentStatus.PENDING,
            payment_date='2026-08-01',
        )
        self.assertFalse(hasattr(payment, 'journal_entry'))

        # start/end are read from GET (they scope the page's queryset), not
        # POST -- match the view's request.GET.get('start')/('end') contract.
        url = _reverse('billing:payment_reconciliation') + '?start=2026-07-01&end=2026-12-31'
        response = self.client.post(url, {
            'reconcile': '1', 'payment_ids': [str(payment.pk)],
        })
        self.assertEqual(response.status_code, 302)

        payment.refresh_from_db()
        self.assertEqual(payment.payment_status, Payment.PaymentStatus.COMPLETED)
        self.assertTrue(hasattr(payment, 'journal_entry'))
        entry = payment.journal_entry
        self.assertEqual(entry.lines.get(account='Cash').debit, _Decimal('30000.00'))
        self.assertEqual(entry.lines.get(account='Accounts Receivable').credit, _Decimal('30000.00'))

    def test_reconciling_twice_does_not_double_post(self):
        from billing.models import JournalEntry, Payment
        payment = Payment.objects.create(
            invoice=self.invoice, amount=_Decimal('15000'),
            payment_method=Payment.Method.CASH,
            payment_status=Payment.PaymentStatus.PENDING,
            payment_date='2026-08-01',
        )
        payment.payment_status = Payment.PaymentStatus.COMPLETED
        payment.save()
        payment.save()  # second save while already Completed must not double-post
        count = JournalEntry.objects.filter(
            reference_doctype='billing.Payment', reference_docname=str(payment.pk),
        ).count()
        self.assertEqual(count, 1)


class RefundAdvanceCreateTests(_TestCase):

    def setUp(self):
        self.user = _User.objects.create_superuser(username='ra_admin', email='raadmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)
        self.customer = _Customer.objects.create(full_name='Refund Customer', phone='9100000001')

    def test_create(self):
        response = self.client.post(_reverse('billing:refund_advance_create'), {
            'customer': self.customer.pk, 'amount': '1000', 'transaction_type': 'refund',
            'reason': 'Cancelled booking', 'status': 'pending',
        })
        self.assertEqual(response.status_code, 302)
        from billing.models import RefundAdvance
        self.assertTrue(RefundAdvance.objects.filter(customer=self.customer).exists())


class GeneralLedgerFilterTests(_TestCase):

    def setUp(self):
        self.user = _User.objects.create_superuser(username='gl_filter_admin', email='glfilter@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)
        from billing.models import JournalEntry, JournalEntryLine
        old = JournalEntry.objects.create(entry_date='2020-01-01', description='Old entry', reference='OLD-1')
        JournalEntryLine.objects.create(entry=old, account='Cash', debit=_Decimal('100'))
        JournalEntryLine.objects.create(entry=old, account='Sales', credit=_Decimal('100'))
        recent = JournalEntry.objects.create(entry_date='2026-08-01', description='Recent entry', reference='RECENT-1')
        JournalEntryLine.objects.create(entry=recent, account='Bank', debit=_Decimal('200'))
        JournalEntryLine.objects.create(entry=recent, account='Sales', credit=_Decimal('200'))

    def test_date_range_filter_excludes_entries_outside_range(self):
        response = self.client.get(_reverse('billing:general_ledger'), {'from_date': '2026-01-01', 'to_date': '2026-12-31'})
        self.assertEqual(response.status_code, 200)
        account_names = {a['name'] for a in response.context['accounts']}
        self.assertIn('Bank', account_names)
        self.assertNotIn('Cash', account_names)

    def test_account_filter_shows_only_the_selected_account(self):
        response = self.client.get(_reverse('billing:general_ledger'), {'account': 'Sales'})
        self.assertEqual(response.status_code, 200)
        account_names = {a['name'] for a in response.context['accounts']}
        self.assertEqual(account_names, {'Sales'})


class JournalEntryDisplayPermissionTests(_TestCase):
    """Uses the 'Accounts' role name (present in accounts.permissions.
    ROLE_PERMISSIONS with 'billing' namespace access) rather than an
    unrecognised role name -- an unrecognised role_name resolves to an
    empty allowed-namespaces list, so RolePermissionMiddleware would 403
    the request at the namespace level before the view-level
    @require_module_action('finance', 'view') check is ever reached,
    making the test pass for the wrong reason."""

    def setUp(self):
        from accounts.models import Role, ModulePermission
        self.role = Role.objects.create(role_name='Accounts')
        ModulePermission.objects.create(role=self.role, module='finance', can_view=False)
        self.user = _User.objects.create(username='no_finance_display', email='nofinance@example.com', role=self.role)
        self.user.set_password('Test-Pass-123!')
        self.user.save()
        self.client.force_login(self.user)
        from billing.models import JournalEntry
        self.entry = JournalEntry.objects.create(entry_date='2026-08-01', description='Blocked entry test', reference='BLOCK-1')

    def test_journal_entry_detail_blocked_when_display_permission_is_off(self):
        response = self.client.get(_reverse('billing:journal_entry_detail', args=[self.entry.pk]))
        self.assertEqual(response.status_code, 403)


class BillingDisplayPermissionAuditTests(_TestCase):
    """Covers the rest of billing's read-only views identified in the Step 5
    audit (Task 10) as exposing specific financial records with only
    @login_required -- the same gap pattern as general_ledger (fixed in
    Task 8) and journal_entry_detail (fixed above). Uses the 'Accounts'
    role (has 'billing' in ROLE_PERMISSIONS) with can_view=False on the
    'finance' ModulePermission so the namespace-level middleware lets the
    request through and only the view-level @require_module_action gate
    is under test.

    Views intentionally NOT covered here (left ungated, see task report):
      - dashboard: billing's landing page, analogous to a namespace-level
        entry point rather than a specific-record view.
      - invoice_search: a cross-reference/search screen the task brief
        specifically flagged as plausibly intended to stay open to anyone
        with billing namespace access.
    """

    def setUp(self):
        from accounts.models import Role, ModulePermission
        self.role = Role.objects.create(role_name='Accounts')
        ModulePermission.objects.create(role=self.role, module='finance', can_view=False)
        self.user = _User.objects.create(username='audit_no_display', email='auditnodisplay@example.com', role=self.role)
        self.user.set_password('Test-Pass-123!')
        self.user.save()
        self.client.force_login(self.user)

        order = _make_order('AUDIT1')
        self.customer = order.customer

        from billing.models import (FinanceLoan, Invoice, InsurancePolicy,
                                     JournalEntry, Payment, RefundAdvance)
        self.invoice = Invoice.objects.create(
            sales_order=order, invoice_number='AUDIT-INV-0001', subtotal=_Decimal('10000'),
            final_amount=_Decimal('10000'), invoice_date='2026-08-01',
        )
        Payment.objects.create(
            invoice=self.invoice, amount=_Decimal('5000'),
            payment_method=Payment.Method.CASH,
            payment_status=Payment.PaymentStatus.COMPLETED,
            payment_date='2026-08-01',
        )
        self.loan = FinanceLoan.objects.create(
            sales_order=order, bank_name='HDFC Bank', loan_amount=_Decimal('60000'),
            loan_status='active', hp_status='not_applicable',
        )
        self.policy = InsurancePolicy.objects.create(
            sales_order=order, provider_name='ICICI Lombard', policy_number='AUDIT-POL-0001',
            premium_amount=_Decimal('3500'), start_date='2026-08-01', end_date='2027-08-01',
        )
        self.refund = RefundAdvance.objects.create(
            customer=self.customer, amount=_Decimal('1000'), transaction_type='refund',
            reason='Audit test', status='pending',
        )
        self.entry = JournalEntry.objects.create(entry_date='2026-08-01', description='Audit entry', reference='AUDIT-JE-1')

    def test_invoice_list_blocked(self):
        response = self.client.get(_reverse('billing:invoice_list'))
        self.assertEqual(response.status_code, 403)

    def test_invoice_detail_blocked(self):
        response = self.client.get(_reverse('billing:invoice_detail', args=[self.invoice.pk]))
        self.assertEqual(response.status_code, 403)

    def test_payment_list_blocked(self):
        response = self.client.get(_reverse('billing:payment_list', args=[self.invoice.pk]))
        self.assertEqual(response.status_code, 403)

    def test_daily_collection_report_blocked(self):
        response = self.client.get(_reverse('billing:daily_collection_report'))
        self.assertEqual(response.status_code, 403)

    def test_loan_list_blocked(self):
        response = self.client.get(_reverse('billing:loan_list'))
        self.assertEqual(response.status_code, 403)

    def test_loan_detail_blocked(self):
        response = self.client.get(_reverse('billing:loan_detail', args=[self.loan.pk]))
        self.assertEqual(response.status_code, 403)

    def test_insurance_policy_list_blocked(self):
        response = self.client.get(_reverse('billing:insurance_policy_list'))
        self.assertEqual(response.status_code, 403)

    def test_insurance_policy_detail_blocked(self):
        response = self.client.get(_reverse('billing:insurance_policy_detail', args=[self.policy.pk]))
        self.assertEqual(response.status_code, 403)

    def test_payment_reconciliation_blocked(self):
        response = self.client.get(_reverse('billing:payment_reconciliation'))
        self.assertEqual(response.status_code, 403)

    def test_refund_advance_list_blocked(self):
        response = self.client.get(_reverse('billing:refund_advance_list'))
        self.assertEqual(response.status_code, 403)

    def test_refund_advance_detail_blocked(self):
        response = self.client.get(_reverse('billing:refund_advance_detail', args=[self.refund.pk]))
        self.assertEqual(response.status_code, 403)

    def test_journal_entry_list_blocked(self):
        response = self.client.get(_reverse('billing:journal_entry_list'))
        self.assertEqual(response.status_code, 403)

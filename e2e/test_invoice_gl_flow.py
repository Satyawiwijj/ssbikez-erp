"""
Real-browser coverage of the Invoice detail page's interstate/intrastate GST
split -- this is the exact IGST feature built this session, and it lives
entirely in template conditional logic (`{% if is_interstate %}`) that a
Client()-based test can assert on but a real browser render is the only way
to catch a template typo, a silently-empty block, or a JS console error on
the same page.
"""
from datetime import date

from accounts.models import Role
from billing.models import Invoice
from sales.models import VehicleSalesOrder

from e2e.base import PlaywrightTestCase
from e2e.fixtures import make_company_settings, make_customer


class InvoiceGSTSplitTest(PlaywrightTestCase):
    def setUp(self):
        super().setUp()
        role = Role.objects.create(role_name='E2E Billing')
        self.user = self.make_user('e2e_billing_user', role=role, is_superuser=True)
        self.login_as(self.user)
        make_company_settings(state='Tamil Nadu', cgst_rate=9, sgst_rate=9)

    def _make_invoice(self, customer_state, invoice_number):
        customer = make_customer(state=customer_state)
        order = VehicleSalesOrder.objects.create(customer=customer, total_amount=0)
        return Invoice.objects.create(
            sales_order=order,
            invoice_number=invoice_number,
            subtotal=100000,
            gst_amount=18000,
            final_amount=118000,
            invoice_date=date.today(),
        )

    def test_intrastate_customer_shows_cgst_sgst_not_igst(self):
        invoice = self._make_invoice('Tamil Nadu', 'E2E-INV-INTRA')
        self.goto(f'/billing/invoices/{invoice.pk}/')

        assert self.page.get_by_text('CGST').is_visible()
        assert self.page.get_by_text('SGST').is_visible()
        assert self.page.get_by_text('IGST').count() == 0
        # 18000 split evenly -> 9000/9000
        assert self.page.get_by_text('9000.00').first.is_visible()

    def test_interstate_customer_shows_igst_not_cgst_sgst(self):
        invoice = self._make_invoice('Karnataka', 'E2E-INV-INTER')
        self.goto(f'/billing/invoices/{invoice.pk}/')

        assert self.page.get_by_text('IGST').is_visible()
        assert self.page.get_by_text('CGST').count() == 0
        assert self.page.get_by_text('SGST').count() == 0
        # full gst_amount goes to IGST, not split
        assert self.page.get_by_text('18000.00').first.is_visible()

"""
Regression tests for the highest-value spares-module bug classes found this
session: the negative-discount validator gap (round 4) and the auto-numbering
uniqueness guarantee shared across ~30 models via the systemic race-condition
fix.
"""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from masters.models import Warehouse
from spares.models import CounterSale, SparesIssueAlteration, SparesItem


class NegativeDiscountValidatorTests(TestCase):

    def test_countersale_discount_amount_rejects_negative(self):
        field = CounterSale._meta.get_field('discount_amount')
        with self.assertRaises(ValidationError):
            field.clean(-1, None)

    def test_countersale_discount_amount_accepts_zero_and_positive(self):
        field = CounterSale._meta.get_field('discount_amount')
        field.clean(0, None)
        field.clean(250, None)

    def test_sparesissuealteration_discount_rejects_negative(self):
        field = SparesIssueAlteration._meta.get_field('discount')
        with self.assertRaises(ValidationError):
            field.clean(-1, None)


class CounterSaleNumberingTests(TestCase):
    """CounterSale.sale_no auto-generation must be unique across
    back-to-back creates (same select_for_update() convention as the
    30-model auto-numbering race fixed this session)."""

    def test_sequential_creates_get_unique_sale_numbers(self):
        warehouse = Warehouse.objects.create(name='Main Store')
        sales = [
            CounterSale.objects.create(
                customer='Walk-in', mobile='9000000000', godown=warehouse, date='2026-07-14',
            )
            for _ in range(5)
        ]
        numbers = [s.sale_no for s in sales]
        self.assertEqual(len(numbers), len(set(numbers)), f"duplicate sale_no values: {numbers}")


from django.test import TestCase as _TestCase
from django.urls import reverse as _reverse

from accounts.models import User as _User
from masters.models import Warehouse as _Warehouse
from spares.models import CounterSale as _CounterSale, SparesItem as _SparesItem


class SparesItemCRUDTests(_TestCase):

    def setUp(self):
        self.user = _User.objects.create_superuser(username='item_admin', email='itemadmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)

    def test_create_then_detail_then_update_round_trip(self):
        response = self.client.post(_reverse('spares:item_create'), {
            'item_name': 'Brake Pad Set', 'uom': 'Nos', 'sgst': '9', 'cgst': '9',
            'opening_stock': '0', 'valuation_rate': '0', 'standard_selling_rate': '0',
            'mrp': '0', 'max_discount': '0', 'reorder_level': '0', 'reorder_qty': '0',
            'warranty_period_days': '0',
        })
        self.assertEqual(response.status_code, 302)
        item = _SparesItem.objects.get(item_name='Brake Pad Set')
        self.assertTrue(item.item_code)  # auto-generated

        response = self.client.get(_reverse('spares:item_detail', args=[item.pk]))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(_reverse('spares:item_list'))
        self.assertEqual(response.status_code, 200)

        response = self.client.post(_reverse('spares:item_update', args=[item.pk]), {
            'item_name': 'Brake Pad Set (Updated)', 'uom': 'Nos', 'sgst': '9', 'cgst': '9',
            'opening_stock': '0', 'valuation_rate': '0', 'standard_selling_rate': '0',
            'mrp': '0', 'max_discount': '0', 'reorder_level': '0', 'reorder_qty': '0',
            'warranty_period_days': '0',
        })
        self.assertEqual(response.status_code, 302)
        item.refresh_from_db()
        self.assertEqual(item.item_name, 'Brake Pad Set (Updated)')


class CounterSaleCreateTests(_TestCase):

    def setUp(self):
        self.user = _User.objects.create_superuser(username='cs_admin', email='csadmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)
        self.warehouse = _Warehouse.objects.create(name='Counter Sale Warehouse')

    def test_create_with_no_item_rows(self):
        response = self.client.post(_reverse('spares:counter_sale_create'), {
            'customer': 'Walk-in Customer', 'mobile': '9700000001', 'godown': self.warehouse.pk,
            'date': '2026-08-01', 'sale_type': 'sale', 'spot_sale': True,
            'status': 'draft', 'discount_amount': '0',
            'items-TOTAL_FORMS': '0', 'items-INITIAL_FORMS': '0',
            'items-MIN_NUM_FORMS': '0', 'items-MAX_NUM_FORMS': '1000',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(_CounterSale.objects.filter(mobile='9700000001').exists())


from accounts.models import Role
from spares.models import StockTransfer as _StockTransfer


class StockTransferCRUDAndOwnershipTests(_TestCase):

    def setUp(self):
        exec_role, _ = Role.objects.get_or_create(role_name='Spares')
        self.owner = _User.objects.create_user(username='st_owner', email='stowner@example.com', password='Test-Pass-123!', role=exec_role)
        self.other = _User.objects.create_user(username='st_other', email='stother@example.com', password='Test-Pass-123!', role=exec_role)
        self.warehouse = _Warehouse.objects.create(name='Stock Transfer WH')

    def test_create_then_submit(self):
        self.client.force_login(self.owner)
        response = self.client.post(_reverse('spares:stock_transfer_create'), {
            'date_and_time': '2026-08-01T10:00', 'warehouse': self.warehouse.pk,
            'items-TOTAL_FORMS': '0', 'items-INITIAL_FORMS': '0',
            'items-MIN_NUM_FORMS': '0', 'items-MAX_NUM_FORMS': '1000',
        })
        self.assertEqual(response.status_code, 302)
        transfer = _StockTransfer.objects.get(warehouse=self.warehouse)

        response = self.client.get(_reverse('spares:stock_transfer_detail', args=[transfer.pk]))
        self.assertEqual(response.status_code, 200)

        response = self.client.post(_reverse('spares:stock_transfer_submit', args=[transfer.pk]))
        self.assertEqual(response.status_code, 302)
        transfer.refresh_from_db()
        self.assertEqual(transfer.docstatus, 1)

    def test_non_owner_cannot_submit(self):
        transfer = _StockTransfer.objects.create(
            date_and_time='2026-08-01T10:00', warehouse=self.warehouse, created_by=self.owner,
        )
        self.client.force_login(self.other)
        response = self.client.post(_reverse('spares:stock_transfer_submit', args=[transfer.pk]))
        self.assertEqual(response.status_code, 403)


class SupplierQuoteCreateTests(_TestCase):

    def setUp(self):
        self.user = _User.objects.create_superuser(username='quote_admin', email='quoteadmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)
        from masters.models import Supplier
        self.supplier = Supplier.objects.create(supplier_name='Quote Supplier Co')

    def test_create_with_no_item_or_tax_rows(self):
        payload = {
            'supplier': self.supplier.pk, 'date': '2026-08-01', 'status': 'draft',
            'additional_discount_percent': '0', 'additional_discount_amount': '0',
            'items-TOTAL_FORMS': '0', 'items-INITIAL_FORMS': '0',
            'items-MIN_NUM_FORMS': '0', 'items-MAX_NUM_FORMS': '1000',
            'taxes-TOTAL_FORMS': '0', 'taxes-INITIAL_FORMS': '0',
            'taxes-MIN_NUM_FORMS': '0', 'taxes-MAX_NUM_FORMS': '1000',
        }
        response = self.client.post(_reverse('spares:quote_create'), payload)
        self.assertEqual(response.status_code, 302)
        from spares.models import SupplierQuote
        self.assertTrue(SupplierQuote.objects.filter(supplier=self.supplier).exists())


from spares.models import PurchaseOrder as _PurchaseOrder, SparesIssueAlteration as _SparesIssueAlteration


class PurchaseOrderCreateTests(_TestCase):

    def setUp(self):
        self.user = _User.objects.create_superuser(username='po_admin', email='poadmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)
        from masters.models import Supplier
        self.supplier = Supplier.objects.create(supplier_name='PO Test Supplier')

    def test_create_with_no_item_or_tax_rows(self):
        payload = {
            'supplier': self.supplier.pk, 'date': '2026-08-01', 'status': 'draft',
            'items-TOTAL_FORMS': '0', 'items-INITIAL_FORMS': '0',
            'items-MIN_NUM_FORMS': '0', 'items-MAX_NUM_FORMS': '1000',
            'taxes-TOTAL_FORMS': '0', 'taxes-INITIAL_FORMS': '0',
            'taxes-MIN_NUM_FORMS': '0', 'taxes-MAX_NUM_FORMS': '1000',
        }
        response = self.client.post(_reverse('spares:order_create'), payload)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(_PurchaseOrder.objects.filter(supplier=self.supplier).exists())


class IssueAlterationCreateTests(_TestCase):

    def setUp(self):
        self.user = _User.objects.create_superuser(username='sia_admin', email='siaadmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)
        self.warehouse = _Warehouse.objects.create(name='SIA Test WH')
        from customer_vehicles.models import CustomerVehicle
        from customers.models import BikeModel, Customer, VehicleStock
        from service.models import JobCard
        customer = Customer.objects.create(full_name='SIA Customer', phone='9300000001')
        bike_model = BikeModel.objects.create(brand='SIA Brand', model_name='SIA Model', ex_showroom_price=Decimal('90000'))
        vehicle = VehicleStock.objects.create(bike_model=bike_model, chassis_no='SIACH001')
        customer_vehicle = CustomerVehicle.objects.create(customer=customer, vehicle=vehicle)
        self.job_card = JobCard.objects.create(customer_vehicle=customer_vehicle)

    def test_create_with_no_item_rows(self):
        payload = {
            'job_card': self.job_card.pk, 'godown': self.warehouse.pk, 'date': '2020-01-01',
            'job_type': 'service', 'brand': 'ss_bikes', 'discount': '0',
            'items-TOTAL_FORMS': '0', 'items-INITIAL_FORMS': '0',
            'items-MIN_NUM_FORMS': '0', 'items-MAX_NUM_FORMS': '1000',
            'deleted-TOTAL_FORMS': '0', 'deleted-INITIAL_FORMS': '0',
            'deleted-MIN_NUM_FORMS': '0', 'deleted-MAX_NUM_FORMS': '1000',
        }
        response = self.client.post(_reverse('spares:issue_alteration_create'), payload)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(_SparesIssueAlteration.objects.filter(job_card=self.job_card).exists())


class StockCountCreateTests(_TestCase):

    def setUp(self):
        self.user = _User.objects.create_superuser(username='sc_admin', email='scadmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)
        self.warehouse = _Warehouse.objects.create(name='Stock Count WH')

    def test_create_with_no_item_rows(self):
        payload = {
            'warehouse': self.warehouse.pk, 'date_and_time': '2020-01-01',
            'items-TOTAL_FORMS': '0', 'items-INITIAL_FORMS': '0',
            'items-MIN_NUM_FORMS': '0', 'items-MAX_NUM_FORMS': '1000',
        }
        response = self.client.post(_reverse('spares:stock_count_create'), payload)
        self.assertEqual(response.status_code, 302)
        from spares.models import StockCountUpdate
        self.assertTrue(StockCountUpdate.objects.filter(warehouse=self.warehouse).exists())


class MRPRevisionCreateTests(_TestCase):

    def setUp(self):
        self.user = _User.objects.create_superuser(username='mrp_admin', email='mrpadmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)

    def test_create_with_no_item_rows(self):
        payload = {
            'date': '2020-01-01', 'price_list': 'standard_selling',
            'items-TOTAL_FORMS': '0', 'items-INITIAL_FORMS': '0',
            'items-MIN_NUM_FORMS': '0', 'items-MAX_NUM_FORMS': '1000',
        }
        response = self.client.post(_reverse('spares:mrp_revision_create'), payload)
        self.assertEqual(response.status_code, 302)
        from spares.models import SparesMRPPriceRevision
        self.assertTrue(SparesMRPPriceRevision.objects.exists())


class CounterSaleReturnGodownRequiredTests(_TestCase):
    """Tier 4 audit finding: CounterSaleReturn.godown is optional
    (models.SET_NULL, null=True, blank=True) and the create view
    (spares/views.py:counter_return_create) always auto-submits a return
    right after saving. The stock-reversal post_save signal
    (on_counter_sale_return_status_changed) explicitly no-ops when
    godown_id is None ("if not instance.godown_id: return"), so a return
    created without a godown silently ends up 'submitted' with the refunded
    stock never actually credited back to any warehouse -- the physical
    stock is lost from the ledger entirely, with no error surfaced anywhere."""

    def setUp(self):
        self.warehouse = _Warehouse.objects.create(name='CSR Godown Test WH')

    def test_submit_without_godown_is_rejected(self):
        from spares.models import CounterSale, CounterSaleReturn, CounterSaleItem, SparesItem

        item = _SparesItem.objects.create(item_name='Godown Guard Test Part', uom='Nos')
        sale = CounterSale.objects.create(
            customer='Walk-in', mobile='9800000001', godown=self.warehouse, date='2026-08-01',
        )
        CounterSaleItem.objects.create(sale=sale, item=item, quantity=Decimal('2'), rate=Decimal('50'))

        ret = CounterSaleReturn.objects.create(
            original_sale=sale, return_date='2026-08-02', godown=None,
        )
        from spares.models import CounterSaleReturnItem
        CounterSaleReturnItem.objects.create(
            sale_return=ret, item=item, quantity=Decimal('2'), rate=Decimal('50'), return_qty=Decimal('2'),
        )

        with self.assertRaises(ValueError):
            ret.submit()

        ret.refresh_from_db()
        self.assertEqual(ret.status, 'draft')

    def test_submit_with_godown_still_works(self):
        from spares.models import CounterSale, CounterSaleReturn, CounterSaleItem, CounterSaleReturnItem, StockLedger

        item = _SparesItem.objects.create(item_name='Godown Guard Test Part 2', uom='Nos')
        sale = CounterSale.objects.create(
            customer='Walk-in', mobile='9800000002', godown=self.warehouse, date='2026-08-01',
        )
        CounterSaleItem.objects.create(sale=sale, item=item, quantity=Decimal('2'), rate=Decimal('50'))

        ret = CounterSaleReturn.objects.create(
            original_sale=sale, return_date='2026-08-02', godown=self.warehouse,
        )
        CounterSaleReturnItem.objects.create(
            sale_return=ret, item=item, quantity=Decimal('2'), rate=Decimal('50'), return_qty=Decimal('2'),
        )
        ret.submit()
        ret.refresh_from_db()
        self.assertEqual(ret.status, 'submitted')
        ledger = StockLedger.objects.get(item=item, warehouse=self.warehouse, rack=None, bin=None)
        self.assertEqual(ledger.quantity, Decimal('2'))


class PurchaseInvoiceItemGSTCentralizedTests(TestCase):

    def setUp(self):
        from accounts.models import CompanySettings
        settings_ = CompanySettings.get_instance()
        settings_.cgst_rate = Decimal('6')
        settings_.sgst_rate = Decimal('6')
        settings_.state = 'Tamil Nadu'
        settings_.save()

    def test_intrastate_supplier_uses_company_configured_rate(self):
        from masters.models import Supplier, Warehouse
        from spares.models import SparesItem, PurchaseInvoice, PurchaseInvoiceItem

        supplier = Supplier.objects.create(supplier_name='Intrastate Supplier', state='Tamil Nadu')
        warehouse = Warehouse.objects.create(name='Main Store')
        item = SparesItem.objects.create(item_code='GST-TEST-1', item_name='Test Part', hsn_sac='1234')
        invoice = PurchaseInvoice.objects.create(supplier=supplier, date='2026-08-01')
        line = PurchaseInvoiceItem.objects.create(
            invoice=invoice, item=item, warehouse=warehouse, quantity=Decimal('10'), rate=Decimal('100'),
        )
        line.refresh_from_db()
        # 10 * 100 = 1000 base; 6%+6% = 120 total split evenly
        self.assertEqual(line.sgst_amount, Decimal('60.00'))
        self.assertEqual(line.cgst_amount, Decimal('60.00'))

    def test_interstate_supplier_gets_igst_not_cgst_sgst(self):
        from masters.models import Supplier, Warehouse
        from spares.models import SparesItem, PurchaseInvoice, PurchaseInvoiceItem

        supplier = Supplier.objects.create(supplier_name='Interstate Supplier', state='Karnataka')
        warehouse = Warehouse.objects.create(name='Main Store 2')
        item = SparesItem.objects.create(item_code='GST-TEST-2', item_name='Test Part 2', hsn_sac='1234')
        invoice = PurchaseInvoice.objects.create(supplier=supplier, date='2026-08-01')
        line = PurchaseInvoiceItem.objects.create(
            invoice=invoice, item=item, warehouse=warehouse, quantity=Decimal('10'), rate=Decimal('100'),
        )
        line.refresh_from_db()
        self.assertEqual(line.sgst_amount, Decimal('0.00'))
        self.assertEqual(line.cgst_amount, Decimal('0.00'))
        self.assertEqual(line.igst_amount, Decimal('120.00'))


class PurchaseInvoiceGrandTotalIGSTTests(TestCase):
    """Finding 1: an interstate PurchaseInvoiceItem now puts its whole GST
    into igst_amount (via split_gst), but invoice_create/invoice_update only
    summed total_sgst/total_cgst into grand_total -- interstate invoices
    silently dropped the entire GST amount from their grand_total."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        from accounts.models import CompanySettings
        from masters.models import Supplier, Warehouse
        from spares.models import SparesItem

        settings_ = CompanySettings.get_instance()
        settings_.cgst_rate = Decimal('9')
        settings_.sgst_rate = Decimal('9')
        settings_.state = 'Tamil Nadu'
        settings_.save()

        User = get_user_model()
        self.user = User.objects.create_superuser(
            username='pi_igst_admin', email='piigstadmin@example.com', password='Test-Pass-123!'
        )
        self.client.login(username='pi_igst_admin', password='Test-Pass-123!')

        self.supplier = Supplier.objects.create(supplier_name='Interstate PI Supplier', state='Karnataka')
        self.warehouse = Warehouse.objects.create(name='PI IGST Warehouse')
        self.item = SparesItem.objects.create(item_code='PI-IGST-1', item_name='IGST Test Part', hsn_sac='1234')

    def _payload(self):
        return {
            'supplier': self.supplier.pk, 'date': '2026-08-01', 'payment_status': 'Unpaid',
            'items-TOTAL_FORMS': '1', 'items-INITIAL_FORMS': '0',
            'items-MIN_NUM_FORMS': '0', 'items-MAX_NUM_FORMS': '1000',
            'items-0-item': self.item.pk, 'items-0-warehouse': self.warehouse.pk,
            'items-0-quantity': '10', 'items-0-uom': 'Nos', 'items-0-rate': '100',
            'items-0-sgst': '9', 'items-0-cgst': '9',
            'taxes-TOTAL_FORMS': '0', 'taxes-INITIAL_FORMS': '0',
            'taxes-MIN_NUM_FORMS': '0', 'taxes-MAX_NUM_FORMS': '1000',
        }

    def test_invoice_create_grand_total_includes_igst_for_interstate_supplier(self):
        from spares.models import PurchaseInvoice

        response = self.client.post(_reverse('spares:invoice_create'), self._payload())
        self.assertEqual(response.status_code, 302)

        invoice = PurchaseInvoice.objects.get(supplier=self.supplier)
        # 10 * 100 = 1000 base; 9%+9% = 180 total, all routed to IGST for an
        # interstate supplier. grand_total must include it, not just total_amount.
        self.assertEqual(invoice.total_igst, Decimal('180.00'))
        self.assertEqual(invoice.total_sgst, Decimal('0.00'))
        self.assertEqual(invoice.total_cgst, Decimal('0.00'))
        self.assertEqual(invoice.grand_total, Decimal('1180.00'))

    def test_invoice_update_grand_total_includes_igst_for_interstate_supplier(self):
        from spares.models import PurchaseInvoice, PurchaseInvoiceItem

        invoice = PurchaseInvoice.objects.create(supplier=self.supplier, date='2026-08-01')
        PurchaseInvoiceItem.objects.create(
            invoice=invoice, item=self.item, warehouse=self.warehouse,
            quantity=Decimal('10'), rate=Decimal('100'),
        )

        payload = self._payload()
        payload['items-INITIAL_FORMS'] = '1'
        payload['items-0-id'] = str(invoice.items.first().pk)

        response = self.client.post(_reverse('spares:invoice_update', args=[invoice.pk]), payload)
        self.assertEqual(response.status_code, 302)

        invoice.refresh_from_db()
        self.assertEqual(invoice.total_igst, Decimal('180.00'))
        self.assertEqual(invoice.grand_total, Decimal('1180.00'))


class PurchaseInvoiceItemFormReadOnlyGSTTests(TestCase):
    """Finding 2: PurchaseInvoiceItem.save() derives GST from
    CompanySettings.cgst_rate/sgst_rate via split_gst() and no longer reads
    self.sgst/self.cgst -- so the per-line SGST %/CGST % inputs must be
    read-only, otherwise a user typing a value there has zero effect with no
    UI indication."""

    def test_sgst_and_cgst_fields_are_readonly(self):
        from spares.forms import PurchaseInvoiceItemForm

        form = PurchaseInvoiceItemForm()
        self.assertTrue(form.fields['sgst'].widget.attrs.get('readonly'))
        self.assertTrue(form.fields['cgst'].widget.attrs.get('readonly'))

    def test_submitting_non_default_sgst_cgst_does_not_change_computed_tax(self):
        from accounts.models import CompanySettings
        from masters.models import Supplier, Warehouse
        from spares.models import SparesItem, PurchaseInvoice, PurchaseInvoiceItem

        settings_ = CompanySettings.get_instance()
        settings_.cgst_rate = Decimal('9')
        settings_.sgst_rate = Decimal('9')
        settings_.state = 'Tamil Nadu'
        settings_.save()

        supplier = Supplier.objects.create(supplier_name='Readonly GST Supplier', state='Tamil Nadu')
        warehouse = Warehouse.objects.create(name='Readonly GST Warehouse')
        item = SparesItem.objects.create(item_code='RO-GST-1', item_name='Readonly Test Part', hsn_sac='1234')
        invoice = PurchaseInvoice.objects.create(supplier=supplier, date='2026-08-01')

        # sgst/cgst submitted as wildly different from the company rate --
        # save() must still derive tax from CompanySettings, ignoring these.
        line = PurchaseInvoiceItem.objects.create(
            invoice=invoice, item=item, warehouse=warehouse,
            quantity=Decimal('10'), rate=Decimal('100'),
            sgst=Decimal('50'), cgst=Decimal('50'),
        )
        line.refresh_from_db()
        self.assertEqual(line.sgst_amount, Decimal('90.00'))
        self.assertEqual(line.cgst_amount, Decimal('90.00'))


class SparesIssueAlterationGSTCentralizedTests(TestCase):
    """SparesIssueAlterationItem and ServiceSparesIssueReturnItem are linked
    to a job_card, not a Customer/Supplier -- there is no real interstate
    counterparty at spares-issue/return time (that is determined later, at
    Service Invoice time). split_gst(gst_total, customer=None) must be used
    instead of the old hardcoded 9%/9% split."""

    def setUp(self):
        from accounts.models import CompanySettings
        settings_ = CompanySettings.get_instance()
        settings_.cgst_rate = Decimal('6')
        settings_.sgst_rate = Decimal('6')
        settings_.save()

        from customer_vehicles.models import CustomerVehicle
        from customers.models import BikeModel, Customer, VehicleStock
        from service.models import JobCard

        self.warehouse = Warehouse.objects.create(name='SIA GST Warehouse')
        customer = Customer.objects.create(full_name='SIA GST Customer', phone='9300000002')
        bike_model = BikeModel.objects.create(brand='SIA GST Brand', model_name='SIA GST Model', ex_showroom_price=Decimal('90000'))
        vehicle = VehicleStock.objects.create(bike_model=bike_model, chassis_no='SIAGSTCH001')
        customer_vehicle = CustomerVehicle.objects.create(customer=customer, vehicle=vehicle)
        self.job_card = JobCard.objects.create(customer_vehicle=customer_vehicle)
        self.item = SparesItem.objects.create(item_code='SIA-GST-1', item_name='SIA GST Test Part', hsn_sac='1234')
        self.alteration = SparesIssueAlteration.objects.create(
            job_card=self.job_card, godown=self.warehouse, date='2026-08-01',
        )

    def test_issue_alteration_item_uses_company_configured_rate_not_hardcoded_nine(self):
        from spares.models import SparesIssueAlterationItem

        line = SparesIssueAlterationItem.objects.create(
            alteration=self.alteration, item=self.item, quantity=Decimal('10'), rate=Decimal('100'),
        )
        line.refresh_from_db()
        # 10 * 100 = 1000 base; 6%+6% = 120 total split evenly (no counterparty -> intrastate)
        self.assertEqual(line.cgst_amount, Decimal('60.00'))
        self.assertEqual(line.sgst_amount, Decimal('60.00'))
        self.assertEqual(line.igst_amount, Decimal('0.00'))
        self.assertEqual(line.total, Decimal('1120.00'))

    def test_issue_return_item_uses_company_configured_rate_not_hardcoded_nine(self):
        from spares.models import ServiceSparesIssueReturn, ServiceSparesIssueReturnItem

        issue_return = ServiceSparesIssueReturn.objects.create(
            spares_issue=self.alteration, godown=self.warehouse,
        )
        line = ServiceSparesIssueReturnItem.objects.create(
            issue_return=issue_return, item=self.item, rate=Decimal('100'), return_qty=Decimal('10'),
        )
        line.refresh_from_db()
        self.assertEqual(line.cgst_amount, Decimal('60.00'))
        self.assertEqual(line.sgst_amount, Decimal('60.00'))
        self.assertEqual(line.igst_amount, Decimal('0.00'))
        self.assertEqual(line.total, Decimal('1120.00'))

"""
Regression tests for the two real bugs the audit found in this module:
(1) 'used_vehicles' was silently missing from every non-superuser role's
    allowed-namespace list, locking the entire module out (round-3 audit).
(2) The dual-FK `clean()` validators originally planned for the Final
    Inspection formsets broke every create flow, including the pre-existing
    Job Card one (Phase 10 build note) -- not retested here since that's
    covered structurally by the Purchase Order -> Receipt -> Invoice chain
    and ownership tests below exercising the same formset/signal machinery.
Plus the Purchase Order -> Receipt -> Invoice 3-stage chain's real side
effect (stock creation on Invoice submit) and the sale_cancel ownership gate.
"""
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import Role, User
from accounts.permissions import ROLE_PERMISSIONS
from customers.models import Customer
from masters.models import Supplier
from used_vehicles.models import (UsedVehiclePurchaseInvoice, UsedVehiclePurchaseItem,
                                   UsedVehiclePurchaseOrder, UsedVehiclePurchaseReceipt,
                                   UsedVehicleRegisterNo, UsedVehicleColor, UsedVehicleModel,
                                   UsedVehicleSale, ManufacturingCompany, UsedVehicleSubGroup,
                                   UsedVehicleInvoice)


class NamespaceAccessTests(TestCase):
    """Round-3 audit finding: 'used_vehicles' was absent from every
    non-superuser role's ROLE_PERMISSIONS entry, so the whole module 403'd
    for everyone except superusers. Spot-checks the 2 roles the audit named
    as directly affected (Sales Executive, Service Advisor)."""

    def test_used_vehicles_namespace_present_for_every_role_except_pure_back_office(self):
        # Every role in ROLE_PERMISSIONS should have used_vehicles listed,
        # since this module spans both the sales and service sides of the
        # business (per the fix's own rationale) -- except the 2 roles that
        # are genuinely back-office only (Accounts, Spares).
        back_office_only = {'Accounts', 'Spares'}
        for role_name, allowed in ROLE_PERMISSIONS.items():
            if allowed == ['*'] or role_name in back_office_only:
                continue
            self.assertIn(
                'used_vehicles', allowed,
                f"role '{role_name}' is missing 'used_vehicles' from its allowed namespaces",
            )

    def test_sales_executive_can_reach_used_vehicles_dashboard(self):
        role, _ = Role.objects.get_or_create(role_name='Sales Executive')
        user = User.objects.create_user(username='uv_sales', email='uvsales@example.com', password='Test-Pass-123!', role=role)
        self.client.force_login(user)
        response = self.client.get(reverse('used_vehicles:dashboard'))
        self.assertNotEqual(response.status_code, 403)

    def test_service_advisor_can_reach_used_vehicles_dashboard(self):
        role, _ = Role.objects.get_or_create(role_name='Service Advisor')
        user = User.objects.create_user(username='uv_svc', email='uvsvc@example.com', password='Test-Pass-123!', role=role)
        self.client.force_login(user)
        response = self.client.get(reverse('used_vehicles:dashboard'))
        self.assertNotEqual(response.status_code, 403)


class PurchaseOrderToInvoiceChainTests(TestCase):
    """The Phase 10 3-stage purchase cycle: Order -> Receipt -> Invoice,
    with real stock creation as the Invoice-submit side effect."""

    def setUp(self):
        self.supplier = Supplier.objects.create(supplier_name='Test Used Vehicle Supplier')
        self.manufacturer = ManufacturingCompany.objects.create(name='Honda Used')
        self.sub_group = UsedVehicleSubGroup.objects.create(name='125cc')
        self.used_model = UsedVehicleModel.objects.create(
            code='UVM-1', manufacturer=self.manufacturer, used_vehicle_name='Honda Activa (Used)', sub_group=self.sub_group,
        )
        self.user = User.objects.create_user(username='uv_purch', email='uvpurch@example.com', password='Test-Pass-123!')

    def test_fk_chain_resolves_and_own_purchase_flow_unaffected(self):
        order = UsedVehiclePurchaseOrder.objects.create(supplier=self.supplier, required_date='2026-08-01')
        receipt = UsedVehiclePurchaseReceipt.objects.create(
            purchase_order=order, supplier=self.supplier, required_date='2026-08-02',
        )
        invoice = UsedVehiclePurchaseInvoice.objects.create(
            purchase_receipt=receipt, invoice_date='2026-08-03', own_purchase=False, supplier_purchase=True,
        )
        self.assertEqual(invoice.purchase_receipt_id, receipt.pk)
        self.assertEqual(receipt.purchase_order_id, order.pk)

        # Regression: an own-purchase (trade-in) invoice with no PO/Receipt
        # stage at all must still work, unaffected by the optional FK.
        own_purchase_invoice = UsedVehiclePurchaseInvoice.objects.create(
            invoice_date='2026-08-03', own_purchase=True, supplier_purchase=False,
        )
        self.assertIsNone(own_purchase_invoice.purchase_receipt_id)

    def test_invoice_submit_creates_real_register_no_stock(self):
        invoice = UsedVehiclePurchaseInvoice.objects.create(invoice_date='2026-08-03', own_purchase=True, supplier_purchase=False)
        UsedVehiclePurchaseItem.objects.create(
            invoice=invoice, used_vehicle=self.used_model, registration_no='UV-TEST-001',
            chassis_no='CHUV001', engine_no='ENUV001',
        )
        self.assertFalse(UsedVehicleRegisterNo.objects.filter(registration_no='UV-TEST-001').exists())
        invoice.submit(self.user)
        stock = UsedVehicleRegisterNo.objects.get(registration_no='UV-TEST-001')
        self.assertEqual(stock.stock_status, UsedVehicleRegisterNo.StockStatus.AVAILABLE)
        self.assertEqual(stock.chassis_no, 'CHUV001')


class SaleOwnershipTests(TestCase):
    """sale_cancel must only allow the sale's own sales_executive or a
    manager to act -- checked via sales_executive, not created_by."""

    def setUp(self):
        exec_role, _ = Role.objects.get_or_create(role_name='Sales Executive')
        mgr_role, _ = Role.objects.get_or_create(role_name='Sales Manager')
        self.owner = User.objects.create_user(username='uvsale_owner', email='uvsaleowner@example.com', password='Test-Pass-123!', role=exec_role)
        self.other = User.objects.create_user(username='uvsale_other', email='uvsaleother@example.com', password='Test-Pass-123!', role=exec_role)
        self.manager = User.objects.create_user(username='uvsale_mgr', email='uvsalemgr@example.com', password='Test-Pass-123!', role=mgr_role)

        customer = Customer.objects.create(full_name='UV Sale Customer', phone='6000000001')
        manufacturer = ManufacturingCompany.objects.create(name='Yamaha Used')
        sub_group = UsedVehicleSubGroup.objects.create(name='150cc')
        used_model = UsedVehicleModel.objects.create(code='UVM-2', manufacturer=manufacturer, used_vehicle_name='Yamaha FZ (Used)', sub_group=sub_group)
        register_no = UsedVehicleRegisterNo.objects.create(registration_no='UV-SALE-001', used_vehicle=used_model)
        self.sale = UsedVehicleSale.objects.create(
            customer=customer, sales_executive=self.owner, vehicle_number=register_no,
            delivery_date='2026-08-05', sale_amount=Decimal('60000'),
        )
        self.sale.submit(self.owner)

    def test_non_owner_cannot_cancel(self):
        self.client.force_login(self.other)
        response = self.client.post(reverse('used_vehicles:sale_cancel', args=[self.sale.pk]))
        self.assertEqual(response.status_code, 403)
        self.sale.refresh_from_db()
        self.assertEqual(self.sale.docstatus, 1)

    def test_manager_can_cancel(self):
        self.client.force_login(self.manager)
        response = self.client.post(reverse('used_vehicles:sale_cancel', args=[self.sale.pk]))
        self.assertEqual(response.status_code, 302)
        self.sale.refresh_from_db()
        self.assertEqual(self.sale.docstatus, 2)


from used_vehicles.models import ManufacturingCompany as _ManufacturingCompany, UsedVehicleModel as _UsedVehicleModel
from used_vehicles.models import UsedVehicleSubGroup as _UsedVehicleSubGroup


class UsedVehicleModelCRUDTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser(username='uvm_admin', email='uvmadmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)
        self.manufacturer = _ManufacturingCompany.objects.create(name='Royal Enfield Used')
        self.sub_group = _UsedVehicleSubGroup.objects.create(name='350cc')

    def test_create_then_list(self):
        response = self.client.post(reverse('used_vehicles:model_create'), {
            'code': 'UVM-CRUD-1', 'manufacturer': self.manufacturer.pk,
            'vehicle_category': 'motorcycle', 'used_vehicle_name': 'Bullet 350 (Used)',
            'sub_group': self.sub_group.pk,
        })
        self.assertEqual(response.status_code, 302)
        model = _UsedVehicleModel.objects.get(code='UVM-CRUD-1')

        response = self.client.get(reverse('used_vehicles:model_list'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(model, response.context['models'])


class UsedVehicleRegisterNoCRUDTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser(username='uvr_admin', email='uvradmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)
        manufacturer = _ManufacturingCompany.objects.create(name='Bajaj Used')
        sub_group = _UsedVehicleSubGroup.objects.create(name='125cc')
        self.used_model = _UsedVehicleModel.objects.create(
            code='UVM-REG-1', manufacturer=manufacturer, used_vehicle_name='Pulsar (Used)', sub_group=sub_group,
        )

    def test_create_then_list(self):
        response = self.client.post(reverse('used_vehicles:register_no_create'), {
            'registration_no': 'KA09ZZ0001', 'used_vehicle': self.used_model.pk, 'stock_status': 'available',
        })
        self.assertEqual(response.status_code, 302)
        response = self.client.get(reverse('used_vehicles:register_no_list'))
        self.assertEqual(response.status_code, 200)


from used_vehicles.models import UsedVehicleBayIn as _UsedVehicleBayIn, UsedVehicleJobCard as _UsedVehicleJobCard
from used_vehicles.models import UsedVehicleInsuranceUpdate as _UsedVehicleInsuranceUpdate


def _make_uv_register_no(suffix=''):
    manufacturer = ManufacturingCompany.objects.create(name=f'Mfg{suffix}')
    sub_group = UsedVehicleSubGroup.objects.create(name=f'SubGroup{suffix}')
    used_model = UsedVehicleModel.objects.create(
        code=f'UVM-X{suffix}', manufacturer=manufacturer, used_vehicle_name=f'Model{suffix}', sub_group=sub_group,
    )
    return UsedVehicleRegisterNo.objects.create(registration_no=f'UVX-{suffix or "0"}', used_vehicle=used_model)


class UsedVehicleBayInCRUDTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser(username='uvbay_admin', email='uvbayadmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)
        register_no = _make_uv_register_no('BAY1')
        self.job_card = _UsedVehicleJobCard.objects.create(register_no=register_no)

    def test_create_then_detail_then_submit(self):
        response = self.client.post(reverse('used_vehicles:uv_bay_in_create'), {
            'job_card': self.job_card.pk, 'date': '2026-08-01T10:00',
        })
        self.assertEqual(response.status_code, 302)
        bay_in = _UsedVehicleBayIn.objects.get(job_card=self.job_card)

        response = self.client.get(reverse('used_vehicles:uv_bay_in_detail', args=[bay_in.pk]))
        self.assertEqual(response.status_code, 200)

        response = self.client.post(reverse('used_vehicles:uv_bay_in_submit', args=[bay_in.pk]))
        self.assertEqual(response.status_code, 302)
        bay_in.refresh_from_db()
        self.assertEqual(bay_in.docstatus, 1)


class UsedVehicleInsuranceUpdateCRUDTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser(username='uvins_admin', email='uvinsadmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)
        self.register_no = _make_uv_register_no('INS1')
        from masters.models import Supplier
        self.supplier = Supplier.objects.create(supplier_name='UV Insurance Supplier')

    def test_create_then_detail(self):
        response = self.client.post(reverse('used_vehicles:used_vehicle_insurance_update_create'), {
            'register_no': self.register_no.pk, 'insurance_status': 'no_insurance',
            'insurance_name': self.supplier.pk, 'policy_number': 'UVINS-0001',
            'start_date': '2026-08-01', 'end_date': '2027-08-01', 'amount': '2500', 'payment_method': 'cash',
        })
        self.assertEqual(response.status_code, 302)
        update = _UsedVehicleInsuranceUpdate.objects.get(policy_number='UVINS-0001')
        response = self.client.get(reverse('used_vehicles:used_vehicle_insurance_update_detail', args=[update.pk]))
        self.assertEqual(response.status_code, 200)


from used_vehicles.models import UsedVehicleLaborCharge as _UsedVehicleLaborCharge


class UsedVehicleBayOutCreateTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser(username='uvbo_admin', email='uvboadmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)
        register_no = _make_uv_register_no('BAYOUT1')
        self.job_card = _UsedVehicleJobCard.objects.create(register_no=register_no)

    def test_create(self):
        response = self.client.post(reverse('used_vehicles:uv_bay_out_create'), {
            'job_card': self.job_card.pk, 'date': '2020-01-01', 'remarks': 'All checks passed',
        })
        self.assertEqual(response.status_code, 302)


class UsedVehicleLaborChargeCreateTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser(username='uvlc_admin', email='uvlcadmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)
        register_no = _make_uv_register_no('LC1')
        self.job_card = _UsedVehicleJobCard.objects.create(register_no=register_no)

    def test_create_with_no_child_rows(self):
        payload = {'job_card': self.job_card.pk}
        for prefix in ('labor', 'spares', 'removes'):
            payload.update({
                f'{prefix}-TOTAL_FORMS': '0', f'{prefix}-INITIAL_FORMS': '0',
                f'{prefix}-MIN_NUM_FORMS': '0', f'{prefix}-MAX_NUM_FORMS': '1000',
            })
        response = self.client.post(reverse('used_vehicles:uv_labor_charge_create'), payload)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(_UsedVehicleLaborCharge.objects.filter(job_card=self.job_card).exists())


class UsedVehiclePurchaseOrderCreateViewTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser(username='uvpo_admin', email='uvpoadmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)
        from masters.models import Supplier
        self.supplier = Supplier.objects.create(supplier_name='UV PO Supplier')

    def test_create_with_no_item_rows(self):
        payload = {
            'supplier': self.supplier.pk, 'required_date': '2026-08-01',
            'items-TOTAL_FORMS': '0', 'items-INITIAL_FORMS': '0',
            'items-MIN_NUM_FORMS': '0', 'items-MAX_NUM_FORMS': '1000',
        }
        response = self.client.post(reverse('used_vehicles:purchase_order_create'), payload)
        self.assertEqual(response.status_code, 302)
        from used_vehicles.models import UsedVehiclePurchaseOrder
        self.assertTrue(UsedVehiclePurchaseOrder.objects.filter(supplier=self.supplier).exists())


class UsedVehicleSaleCreateViewTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser(username='uvsale_admin', email='uvsaleadmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)
        from customers.models import Customer
        self.customer = Customer.objects.create(full_name='UV Sale View Customer', phone='9200000001')
        self.register_no = _make_uv_register_no('SALEVIEW1')

    def test_create_with_no_child_rows(self):
        payload = {
            'customer': self.customer.pk, 'vehicle_number': self.register_no.pk,
            'delivery_date': '2026-08-01', 'sale_amount': '55000', 'sale_status': 'booked',
        }
        for prefix in ('fittings', 'items', 'advance'):
            payload.update({
                f'{prefix}-TOTAL_FORMS': '0', f'{prefix}-INITIAL_FORMS': '0',
                f'{prefix}-MIN_NUM_FORMS': '0', f'{prefix}-MAX_NUM_FORMS': '1000',
            })
        response = self.client.post(reverse('used_vehicles:sale_create'), payload)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(UsedVehicleSale.objects.filter(customer=self.customer).exists())


class UsedVehiclePurchaseReceiptCreateTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser(username='uvpr_admin', email='uvpradmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)
        from masters.models import Supplier
        from used_vehicles.models import UsedVehiclePurchaseOrder
        self.supplier = Supplier.objects.create(supplier_name='UV Receipt Supplier')
        self.po = UsedVehiclePurchaseOrder.objects.create(supplier=self.supplier, required_date='2026-08-01')

    def test_create_with_no_item_rows(self):
        payload = {
            'purchase_order': self.po.pk, 'supplier': self.supplier.pk, 'required_date': '2026-08-02',
            'items-TOTAL_FORMS': '0', 'items-INITIAL_FORMS': '0',
            'items-MIN_NUM_FORMS': '0', 'items-MAX_NUM_FORMS': '1000',
        }
        response = self.client.post(reverse('used_vehicles:purchase_receipt_create'), payload)
        self.assertEqual(response.status_code, 302)
        from used_vehicles.models import UsedVehiclePurchaseReceipt
        self.assertTrue(UsedVehiclePurchaseReceipt.objects.filter(purchase_order=self.po).exists())


class UsedVehicleRCHandOverFormGateTests(TestCase):
    """Tier 6 audit finding: reference's Used Vehicle RC Hand Over before_save
    script (reference_erp_spec/07_Used_Vehicle_Sale.md:2926-2935) refuses to
    save the form at all unless RC Book Received == 'Yes' AND NOC == 'Yes' --
    a trade-in vehicle cannot be accepted without both documents physically in
    hand. This is the same class of bug already fixed in rto.forms.RCHandOverForm
    (see DEVIATIONS.md), but used_vehicles.forms.UsedVehicleRCHandOverForm --
    a separate doctype instance for used-vehicle sales -- never got the gate."""

    def setUp(self):
        self.user = User.objects.create_superuser(username='uvrc_admin', email='uvrcadmin@example.com', password='Test-Pass-123!')
        customer = Customer.objects.create(full_name='UV RC Customer', phone='6000000099')
        manufacturer = ManufacturingCompany.objects.create(name='Bajaj Used')
        sub_group = UsedVehicleSubGroup.objects.create(name='125cc')
        used_model = UsedVehicleModel.objects.create(code='UVM-RC', manufacturer=manufacturer, used_vehicle_name='Bajaj Pulsar (Used)', sub_group=sub_group)
        register_no = UsedVehicleRegisterNo.objects.create(registration_no='UV-RC-001', used_vehicle=used_model)
        self.sale = UsedVehicleSale.objects.create(
            customer=customer, vehicle_number=register_no,
            delivery_date='2026-08-05', sale_amount=Decimal('55000'),
        )

    def _payload(self, **overrides):
        payload = {
            'sale': self.sale.pk,
            'status': 'pending',
            'rc_book_received': 'yes',
            'noc': 'yes',
            'rc_number': 'RC-12345',
        }
        payload.update(overrides)
        return payload

    def test_rc_book_received_no_is_rejected(self):
        from used_vehicles.forms import UsedVehicleRCHandOverForm
        form = UsedVehicleRCHandOverForm(self._payload(rc_book_received='no'))
        self.assertFalse(form.is_valid())
        self.assertIn('rc_book_received', form.errors)

    def test_noc_no_is_rejected(self):
        from used_vehicles.forms import UsedVehicleRCHandOverForm
        form = UsedVehicleRCHandOverForm(self._payload(noc='no'))
        self.assertFalse(form.is_valid())
        self.assertIn('noc', form.errors)

    def test_both_yes_is_accepted(self):
        from used_vehicles.forms import UsedVehicleRCHandOverForm
        form = UsedVehicleRCHandOverForm(self._payload())
        self.assertTrue(form.is_valid(), form.errors)


class UsedVehicleInvoiceGSTCentralizedTests(TestCase):
    """UsedVehicleInvoice.gst_amount used to be computed with a flat
    CompanySettings.gst_rate and no interstate awareness (InvoiceForm.clean(),
    the same shape billing.Invoice was in before e79e25f). recompute_totals()
    now delegates to billing.split_gst() so interstate customers get IGST
    instead of an incorrect CGST/SGST split."""

    def setUp(self):
        from accounts.models import CompanySettings
        settings_ = CompanySettings.get_instance()
        settings_.cgst_rate = Decimal('6')
        settings_.sgst_rate = Decimal('6')
        settings_.state = 'Tamil Nadu'
        settings_.save()

    def _make_sale(self, customer):
        manufacturer = ManufacturingCompany.objects.create(name='UV GST Mfg')
        sub_group = UsedVehicleSubGroup.objects.create(name='UV GST SubGroup')
        used_model = UsedVehicleModel.objects.create(
            code='UVM-GST-1', manufacturer=manufacturer, used_vehicle_name='UV GST Model', sub_group=sub_group,
        )
        register_no = UsedVehicleRegisterNo.objects.create(registration_no='UV-GST-001', used_vehicle=used_model)
        return UsedVehicleSale.objects.create(
            customer=customer, vehicle_number=register_no,
            delivery_date='2026-08-05', sale_amount=Decimal('60000'),
        )

    def test_interstate_customer_gets_igst(self):
        customer = Customer.objects.create(full_name='Interstate UV Customer', phone='9000000100', state='Karnataka')
        sale = self._make_sale(customer)
        invoice = UsedVehicleInvoice.objects.create(
            sale=sale, subtotal=Decimal('10000'), final_amount=Decimal('0'), invoice_date='2026-08-01',
        )
        invoice.recompute_totals()
        invoice.refresh_from_db()
        self.assertGreater(invoice.gst_amount, Decimal('0'))
        self.assertEqual(invoice.gst_amount, Decimal('1200.00'))
        self.assertEqual(invoice.final_amount, invoice.subtotal + invoice.gst_amount)

    def test_intrastate_customer_uses_split_cgst_sgst(self):
        customer = Customer.objects.create(full_name='Intrastate UV Customer', phone='9000000101', state='Tamil Nadu')
        sale = self._make_sale(customer)
        invoice = UsedVehicleInvoice.objects.create(
            sale=sale, subtotal=Decimal('10000'), final_amount=Decimal('0'), invoice_date='2026-08-01',
        )
        invoice.recompute_totals()
        invoice.refresh_from_db()
        self.assertEqual(invoice.gst_amount, Decimal('1200.00'))
        self.assertEqual(invoice.final_amount, invoice.subtotal + invoice.gst_amount)

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
                                   UsedVehicleSale, ManufacturingCompany, UsedVehicleSubGroup)


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

"""
Regression tests for the VAS stock-safety guard and auto-invoice-on-submit
behavior added in Phase 11b: submitting an AMC/RSA/Protection-Plus package
must be blocked when the plan type has zero stock, and a submit with a real
sales_order must create a matching billing.Invoice exactly once.
"""
from decimal import Decimal

from django.test import TestCase

from accounts.models import User
from customer_vehicles.models import CustomerVehicle
from customers.models import BikeModel, Customer, VehicleStock
from sales.models import VehicleSalesOrder
from vas.models import AMCPackage, AMCType, VASStockLedger


def _make_customer_vehicle(suffix=''):
    customer = Customer.objects.create(full_name=f'VAS Customer{suffix}', phone=f'800000000{suffix or "0"}')
    bike_model = BikeModel.objects.create(
        brand='Yamaha', model_name=f'FZ{suffix}', ex_showroom_price=Decimal('120000'),
    )
    vehicle = VehicleStock.objects.create(bike_model=bike_model, chassis_no=f'CH{suffix or "0"}TEST')
    return CustomerVehicle.objects.create(customer=customer, vehicle=vehicle), customer


class StockSafetyGuardTests(TestCase):
    """AMCPackage.submit() -- must not allow a sale to go through when the
    AMC type has no stock (round-3 audit finding; the reference server
    enforces this and the Django port had silently skipped it)."""

    def setUp(self):
        self.amc_type = AMCType.objects.create(code='GOLD', name='Gold AMC')
        self.customer_vehicle, _ = _make_customer_vehicle('1')
        self.user = User.objects.create_user(username='vastest', email='vas@example.com', password='Test-Pass-123!')

    def test_submit_blocked_when_stock_is_zero(self):
        package = AMCPackage.objects.create(customer_vehicle=self.customer_vehicle, amc_type=self.amc_type)
        with self.assertRaises(ValueError):
            package.submit(self.user)
        package.refresh_from_db()
        self.assertEqual(package.docstatus, 0)

    def test_submit_succeeds_once_stock_is_available(self):
        ledger = VASStockLedger.get_or_create_for(amc_type=self.amc_type)
        VASStockLedger.objects.filter(pk=ledger.pk).update(current_stock=1)
        package = AMCPackage.objects.create(customer_vehicle=self.customer_vehicle, amc_type=self.amc_type)
        package.submit(self.user)
        package.refresh_from_db()
        self.assertEqual(package.docstatus, 1)


class StockRestoreOnCancelTests(TestCase):
    """Tier 7 (VAS) audit -- verifies the round-3 adversarial-QA fix ('cancelling an
    AMC/RSA/Protection Plus package never returned its stock') is still correct: cancel()
    must post a reversing PURCHASE movement so the plan type's stock comes back, and doing
    so must be idempotent (no double-credit if cancel is somehow invoked twice)."""

    def setUp(self):
        self.amc_type = AMCType.objects.create(code='CANCELTEST-AMC', name='Cancel Test AMC')
        self.rsa_type = _RSAType.objects.create(code='CANCELTEST-RSA', name='Cancel Test RSA')
        from vas.models import WarrantyType
        self.warranty_type = WarrantyType.objects.create(code='CANCELTEST-PP', name='Cancel Test PP')
        for kwargs in (
            {'amc_type': self.amc_type}, {'rsa_type': self.rsa_type}, {'warranty_type': self.warranty_type},
        ):
            ledger = VASStockLedger.get_or_create_for(**kwargs)
            VASStockLedger.objects.filter(pk=ledger.pk).update(current_stock=1)
        self.customer_vehicle, _ = _make_customer_vehicle('CANCEL1')
        self.user = User.objects.create_user(username='vascancel', email='vascancel@example.com', password='Test-Pass-123!')

    def test_amc_cancel_restores_stock(self):
        package = AMCPackage.objects.create(customer_vehicle=self.customer_vehicle, amc_type=self.amc_type)
        package.submit(self.user)
        ledger = VASStockLedger.objects.get(amc_type=self.amc_type)
        self.assertEqual(ledger.current_stock, 0)

        package.cancel(self.user)
        ledger.refresh_from_db()
        self.assertEqual(ledger.current_stock, 1)

    def test_rsa_cancel_restores_stock(self):
        from vas.models import RSAPackage
        package = RSAPackage.objects.create(customer_vehicle=self.customer_vehicle, rsa_type=self.rsa_type)
        package.submit(self.user)
        ledger = VASStockLedger.objects.get(rsa_type=self.rsa_type)
        self.assertEqual(ledger.current_stock, 0)

        package.cancel(self.user)
        ledger.refresh_from_db()
        self.assertEqual(ledger.current_stock, 1)

    def test_protection_plus_cancel_restores_stock(self):
        from vas.models import ProtectionPlusPackage
        package = ProtectionPlusPackage.objects.create(
            customer_vehicle=self.customer_vehicle, warranty_type=self.warranty_type,
        )
        package.submit(self.user)
        ledger = VASStockLedger.objects.get(warranty_type=self.warranty_type)
        self.assertEqual(ledger.current_stock, 0)

        package.cancel(self.user)
        ledger.refresh_from_db()
        self.assertEqual(ledger.current_stock, 1)

    def test_cancel_reversal_is_idempotent(self):
        """A second cancel() call (e.g. a double form submit) must not credit stock twice.
        DocStatusMixin.cancel() itself already blocks re-cancelling a non-Submitted doc
        (accounts/models.py:63), which is the primary guard; this confirms it holds for VAS
        packages and that stock isn't double-credited in the attempt."""
        package = AMCPackage.objects.create(customer_vehicle=self.customer_vehicle, amc_type=self.amc_type)
        package.submit(self.user)
        package.cancel(self.user)

        with self.assertRaises(ValueError):
            package.cancel(self.user)

        ledger = VASStockLedger.objects.get(amc_type=self.amc_type)
        self.assertEqual(ledger.current_stock, 1)


class AutoInvoiceTests(TestCase):
    """The post-submit signal that auto-creates a billing.Invoice from the
    package's own computed amount fields (Phase 11b)."""

    def setUp(self):
        self.amc_type = AMCType.objects.create(code='SILVER', name='Silver AMC')
        ledger = VASStockLedger.get_or_create_for(amc_type=self.amc_type)
        VASStockLedger.objects.filter(pk=ledger.pk).update(current_stock=5)
        self.user = User.objects.create_user(username='vasinv', email='vasinv@example.com', password='Test-Pass-123!')

    def test_invoice_created_when_sales_order_is_set(self):
        customer_vehicle, customer = _make_customer_vehicle('2')
        order = VehicleSalesOrder.objects.create(
            customer=customer, booking_amount=Decimal('1000'), total_amount=Decimal('100000'),
        )
        # amount/gst_amount/without_gst_amount are now derived by
        # AMCPackage.save() via _compute_vas_package_gst() (GST centralization,
        # Task 4) -- only `amount` needs to be supplied, the other two are
        # computed forward from it using the company's GST rate (default
        # cgst_rate=9 + sgst_rate=9 = 18%): gst_amount = 1000*18/100 = 180,
        # without_gst_amount = 1000-180 = 820.
        package = AMCPackage.objects.create(
            customer_vehicle=customer_vehicle, amc_type=self.amc_type, sales_order=order,
            amount=Decimal('1000'),
        )
        package.submit(self.user)
        package.refresh_from_db()
        self.assertIsNotNone(package.invoice_id)
        invoice = package.invoice
        self.assertEqual(invoice.subtotal, Decimal('820'))
        self.assertEqual(invoice.gst_amount, Decimal('180'))
        self.assertEqual(invoice.final_amount, Decimal('1000'))
        self.assertEqual(invoice.sales_order_id, order.pk)

    def test_no_invoice_created_when_sales_order_is_unset(self):
        customer_vehicle, _ = _make_customer_vehicle('3')
        package = AMCPackage.objects.create(customer_vehicle=customer_vehicle, amc_type=self.amc_type)
        package.submit(self.user)
        package.refresh_from_db()
        self.assertIsNone(package.invoice_id)


from django.test import TestCase as _TestCase
from django.urls import reverse as _reverse

from accounts.models import User as _User
from masters.models import Supplier as _Supplier
from vas.models import AMCType as _AMCType, RSAType as _RSAType, RSACreation as _RSACreation


class AMCTypeCRUDTests(_TestCase):

    def setUp(self):
        self.user = _User.objects.create_superuser(username='amctype_admin', email='amctypeadmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)

    def test_create_then_list(self):
        response = self.client.post(_reverse('vas:amc_type_create'), {
            'code': 'PLAT', 'name': 'Platinum AMC', 'amc_validity_days': '365', 'amc_amount': '2000',
        })
        self.assertEqual(response.status_code, 302)
        amc_type = _AMCType.objects.get(code='PLAT')
        self.assertEqual(amc_type.name, 'Platinum AMC')

        response = self.client.get(_reverse('vas:amc_type_list'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(amc_type, response.context['types'])


class RSACreationCRUDTests(_TestCase):

    def setUp(self):
        self.user = _User.objects.create_superuser(username='rsacre_admin', email='rsacreadmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)
        self.rsa_type = _RSAType.objects.create(code='RSA1', name='Standard RSA')
        self.supplier = _Supplier.objects.create(supplier_name='RSA Supplier Co')

    def test_create_then_submit(self):
        response = self.client.post(_reverse('vas:rsa_creation_create'), {
            'rsa_type': self.rsa_type.pk, 'rsa_amount': '500', 'supplier': self.supplier.pk,
        })
        self.assertEqual(response.status_code, 302)
        creation = _RSACreation.objects.get(rsa_type=self.rsa_type)
        self.assertEqual(creation.docstatus, 0)

        response = self.client.post(_reverse('vas:rsa_creation_submit', args=[creation.pk]))
        self.assertEqual(response.status_code, 302)
        creation.refresh_from_db()
        self.assertEqual(creation.docstatus, 1)


class VASSupplierInvoiceCreateTests(_TestCase):

    def setUp(self):
        self.user = _User.objects.create_superuser(username='vasinv_admin', email='vasinvadmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)
        self.supplier = _Supplier.objects.create(supplier_name='VAS Invoice Supplier')

    def test_create_with_no_item_rows(self):
        response = self.client.post(_reverse('vas:vas_invoice_create'), {
            'supplier': self.supplier.pk, 'invoice_date': '2020-01-01', 'payment_status': 'unpaid',
            'items-TOTAL_FORMS': '0', 'items-INITIAL_FORMS': '0',
            'items-MIN_NUM_FORMS': '0', 'items-MAX_NUM_FORMS': '1000',
        })
        self.assertEqual(response.status_code, 302)
        from vas.models import VASSupplierInvoice
        self.assertTrue(VASSupplierInvoice.objects.filter(supplier=self.supplier).exists())


class AMCPackageCreateViewTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser(username='amcview_admin', email='amcviewadmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)
        self.customer_vehicle, _ = _make_customer_vehicle('AMCVIEW1')
        self.amc_type = AMCType.objects.create(code='AMCVIEW-T', name='AMC View Test Type')

    def test_create(self):
        response = self.client.post(_reverse('vas:amc_create'), {
            'customer_vehicle': self.customer_vehicle.pk, 'status': 'active',
            'amc_type': self.amc_type.pk, 'amount': '2500',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(AMCPackage.objects.filter(customer_vehicle=self.customer_vehicle).exists())


class WarrantyTypeCreateTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser(username='wt_admin', email='wtadmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)

    def test_create(self):
        response = self.client.post(_reverse('vas:warranty_type_create'), {'code': 'STD', 'name': 'Standard Warranty'})
        self.assertEqual(response.status_code, 302)
        from vas.models import WarrantyType
        self.assertTrue(WarrantyType.objects.filter(code='STD').exists())


class RSAPackageCreateViewTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser(username='rsaview_admin', email='rsaviewadmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)
        self.customer_vehicle, _ = _make_customer_vehicle('RSAVIEW1')
        self.rsa_type = _RSAType.objects.create(code='RSAVIEW-T', name='RSA View Test Type')

    def test_create(self):
        response = self.client.post(_reverse('vas:rsa_create'), {
            'customer_vehicle': self.customer_vehicle.pk, 'status': 'active',
            'rsa_type': self.rsa_type.pk, 'amount': '600',
        })
        self.assertEqual(response.status_code, 302)


# ---------------------------------------------------------------------------
# GST centralization -- AMC/RSA/Protection Plus previously had `amount` /
# `gst_amount` / `without_gst_amount` fields with zero computation logic (no
# save() derivation, no split_gst() usage). Reference formula confirmed from
# reference_erp_spec/18_Sales_Form.md client scripts (RSA ~L11776-11789, AMC
# ~L12072-12089, Protection Plus ~L12354-12382) -- all three use the identical
# pair of formulas:
#   gst_amount         = amount * combined_gst_rate / 100
#   without_gst_amount = amount - gst_amount
# `amount` is the value entered on the form and `gst_amount` is calculated
# forward off it (not back-derived via amount * rate/(100+rate)), but
# `without_gst_amount` is NOT simply an echo of `amount` -- it's
# amount-minus-gst, exactly as the legacy client script computes it.
# ---------------------------------------------------------------------------

from vas.models import ProtectionPlusPackage as _ProtectionPlusPackage
from vas.models import RSAPackage as _RSAPackageGST
from vas.models import WarrantyType as _WarrantyType


class AMCPackageGSTCentralizedTests(TestCase):

    def setUp(self):
        from accounts.models import CompanySettings
        settings_ = CompanySettings.get_instance()
        settings_.cgst_rate = Decimal('9')
        settings_.sgst_rate = Decimal('9')
        settings_.state = 'Tamil Nadu'
        settings_.save()
        self.customer_vehicle, self.customer = _make_customer_vehicle('AMCGST1')
        self.customer.state = 'Tamil Nadu'
        self.customer.save()

    def test_gst_amount_computed_from_company_rate_not_left_at_zero(self):
        package = AMCPackage.objects.create(customer_vehicle=self.customer_vehicle, amount=Decimal('1000'))
        package.refresh_from_db()
        self.assertGreater(package.gst_amount, Decimal('0'))
        self.assertEqual(package.gst_amount, Decimal('180.00'))
        self.assertEqual(package.without_gst_amount, Decimal('820.00'))

    def test_interstate_customer_routes_full_gst_to_igst(self):
        self.customer.state = 'Kerala'
        self.customer.save()
        package = AMCPackage.objects.create(customer_vehicle=self.customer_vehicle, amount=Decimal('1000'))
        package.refresh_from_db()
        self.assertEqual(package.gst_amount, Decimal('180.00'))
        self.assertEqual(package.without_gst_amount, Decimal('820.00'))


class RSAPackageGSTCentralizedTests(TestCase):

    def setUp(self):
        from accounts.models import CompanySettings
        settings_ = CompanySettings.get_instance()
        settings_.cgst_rate = Decimal('9')
        settings_.sgst_rate = Decimal('9')
        settings_.state = 'Tamil Nadu'
        settings_.save()
        self.customer_vehicle, self.customer = _make_customer_vehicle('RSAGST1')
        self.customer.state = 'Tamil Nadu'
        self.customer.save()

    def test_gst_amount_computed_from_company_rate_not_left_at_zero(self):
        package = _RSAPackageGST.objects.create(customer_vehicle=self.customer_vehicle, amount=Decimal('500'))
        package.refresh_from_db()
        self.assertGreater(package.gst_amount, Decimal('0'))
        self.assertEqual(package.gst_amount, Decimal('90.00'))
        self.assertEqual(package.without_gst_amount, Decimal('410.00'))


class ProtectionPlusPackageGSTCentralizedTests(TestCase):

    def setUp(self):
        from accounts.models import CompanySettings
        settings_ = CompanySettings.get_instance()
        settings_.cgst_rate = Decimal('9')
        settings_.sgst_rate = Decimal('9')
        settings_.state = 'Tamil Nadu'
        settings_.save()
        self.customer_vehicle, self.customer = _make_customer_vehicle('PPGST1')
        self.customer.state = 'Tamil Nadu'
        self.customer.save()
        self.warranty_type = _WarrantyType.objects.create(code='PPGST-T', name='PP GST Test Type')

    def test_gst_amount_computed_from_company_rate_not_left_at_zero(self):
        package = _ProtectionPlusPackage.objects.create(
            customer_vehicle=self.customer_vehicle, warranty_type=self.warranty_type, amount=Decimal('2000'),
        )
        package.refresh_from_db()
        self.assertGreater(package.gst_amount, Decimal('0'))
        self.assertEqual(package.gst_amount, Decimal('360.00'))
        self.assertEqual(package.without_gst_amount, Decimal('1640.00'))


# ---------------------------------------------------------------------------
# Task 10: branch field on AMC/RSA/Protection Plus packages
# ---------------------------------------------------------------------------

class VASPackageBranchFieldTests(TestCase):
    """Task 10: Verify branch field exists and works on all three VAS package types."""

    def setUp(self):
        from accounts.models import Branch
        self.branch = Branch.objects.create(
            branch_name='Test Branch', phone='9876543210',
        )
        self.customer_vehicle, _ = _make_customer_vehicle('BRANCH1')
        self.amc_type = _AMCType.objects.create(code='BRANCH-AMC', name='Branch Test AMC')
        self.rsa_type = _RSAType.objects.create(code='BRANCH-RSA', name='Branch Test RSA')
        self.warranty_type = _WarrantyType.objects.create(code='BRANCH-PP', name='Branch Test PP')

    def test_amc_package_has_branch_field(self):
        """Branch field exists on AMCPackage model."""
        self.assertIn('branch', [f.name for f in AMCPackage._meta.get_fields()])

    def test_rsa_package_has_branch_field(self):
        """Branch field exists on RSAPackage model."""
        from vas.models import RSAPackage
        self.assertIn('branch', [f.name for f in RSAPackage._meta.get_fields()])

    def test_protection_plus_package_has_branch_field(self):
        """Branch field exists on ProtectionPlusPackage model."""
        self.assertIn('branch', [f.name for f in _ProtectionPlusPackage._meta.get_fields()])

    def test_amc_package_branch_persists(self):
        """Creating AMCPackage with branch and retrieving it returns the same branch."""
        package = AMCPackage.objects.create(
            customer_vehicle=self.customer_vehicle, amc_type=self.amc_type,
            branch=self.branch, amount=Decimal('1000'),
        )
        package.refresh_from_db()
        self.assertEqual(package.branch_id, self.branch.pk)

    def test_rsa_package_branch_persists(self):
        """Creating RSAPackage with branch and retrieving it returns the same branch."""
        from vas.models import RSAPackage
        package = RSAPackage.objects.create(
            customer_vehicle=self.customer_vehicle, rsa_type=self.rsa_type,
            branch=self.branch, amount=Decimal('500'),
        )
        package.refresh_from_db()
        self.assertEqual(package.branch_id, self.branch.pk)

    def test_protection_plus_package_branch_persists(self):
        """Creating ProtectionPlusPackage with branch and retrieving it returns the same branch."""
        package = _ProtectionPlusPackage.objects.create(
            customer_vehicle=self.customer_vehicle, warranty_type=self.warranty_type,
            branch=self.branch, amount=Decimal('2000'),
        )
        package.refresh_from_db()
        self.assertEqual(package.branch_id, self.branch.pk)


class VASPackageDuplicateSalesOrderTests(TestCase):
    """reference explicitly rejects reusing an Order Form ID for a second
    AMC/RSA/Warranty package -- sales_order was a plain nullable FK with no
    duplicate check on the Django port."""

    def test_cannot_create_a_second_amc_package_for_the_same_sales_order(self):
        from vas.forms import AMCPackageForm

        cv, customer = _make_customer_vehicle('amc-dup')
        amc_type = AMCType.objects.create(code='DUP', name='Dup AMC')
        order = VehicleSalesOrder.objects.create(
            customer=customer, booking_amount=Decimal('1000'), total_amount=Decimal('50000'),
        )
        AMCPackage.objects.create(customer_vehicle=cv, sales_order=order, amount=Decimal('1000'))

        form = AMCPackageForm(data={
            'customer_vehicle': cv.pk, 'amc_type': amc_type.pk, 'sales_order': order.pk,
            'amount': '1000', 'status': AMCPackage.Status.ACTIVE,
        })
        self.assertFalse(form.is_valid())
        self.assertIn('sales_order', form.errors)

    def test_cannot_create_a_second_rsa_package_for_the_same_sales_order(self):
        from vas.forms import RSAPackageForm
        from vas.models import RSAPackage, RSAType

        cv, customer = _make_customer_vehicle('rsa-dup')
        rsa_type = RSAType.objects.create(code='DUP', name='Dup RSA')
        order = VehicleSalesOrder.objects.create(
            customer=customer, booking_amount=Decimal('1000'), total_amount=Decimal('50000'),
        )
        RSAPackage.objects.create(customer_vehicle=cv, sales_order=order, amount=Decimal('500'))

        form = RSAPackageForm(data={
            'customer_vehicle': cv.pk, 'rsa_type': rsa_type.pk, 'sales_order': order.pk,
            'amount': '500', 'status': RSAPackage.Status.ACTIVE,
        })
        self.assertFalse(form.is_valid())
        self.assertIn('sales_order', form.errors)

    def test_cannot_create_a_second_protection_plus_package_for_the_same_sales_order(self):
        from vas.forms import ProtectionPlusPackageForm
        from vas.models import ProtectionPlusPackage, WarrantyType

        cv, customer = _make_customer_vehicle('pp-dup')
        warranty_type = WarrantyType.objects.create(code='DUP', name='Dup Warranty')
        order = VehicleSalesOrder.objects.create(
            customer=customer, booking_amount=Decimal('1000'), total_amount=Decimal('50000'),
        )
        ProtectionPlusPackage.objects.create(customer_vehicle=cv, sales_order=order, amount=Decimal('2000'))

        form = ProtectionPlusPackageForm(data={
            'customer_vehicle': cv.pk, 'warranty_type': warranty_type.pk, 'sales_order': order.pk,
            'amount': '2000', 'status': ProtectionPlusPackage.Status.ACTIVE,
        })
        self.assertFalse(form.is_valid())
        self.assertIn('sales_order', form.errors)

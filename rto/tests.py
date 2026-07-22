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
            'noc': 'yes', 'vehicle_received': 'yes',
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
        from rto.models import RegistrationArea
        self.area = RegistrationArea.objects.create(name='F20 Test Area')

    def test_create_then_detail(self):
        response = self.client.post(_reverse('rto:form20_creation_create'), {
            'sales_order': self.order.pk, 'engine_no': 'ENF20001', 'frame_no': 'FRF20001', 'application_no': 'APP-0001',
            'registration_area': self.area.pk,
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
        from rto.models import RegistrationArea
        self.area = RegistrationArea.objects.create(name='RegNo Test Area')

    def test_create(self):
        response = self.client.post(_reverse('rto:registration_no_creation_create'), {
            'sales_order': self.order.pk, 'reg_no': 'KA05REG0001', 'status': 'open',
            'registration_area': self.area.pk,
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


from rto.models import NumberOrderEntryCreation as _NumberOrderEntryCreation


class NumberOrderEntryCreationCRUDTests(_TestCase):

    def setUp(self):
        self.user = _User.objects.create_superuser(username='noe_admin', email='noeadmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)
        self.order = _make_order('NOE1')
        from masters.models import Supplier
        self.agent = Supplier.objects.create(supplier_name='NOE Agent Co')

    def test_create(self):
        response = self.client.post(_reverse('rto:number_order_entry_create'), {
            'sales_order': self.order.pk, 'agent': self.agent.pk, 'application_type': 'NB',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(_NumberOrderEntryCreation.objects.filter(sales_order=self.order).exists())


class RCBookIssueCreateTests(_TestCase):

    def setUp(self):
        self.user = _User.objects.create_superuser(username='rcbi_admin', email='rcbiadmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)
        order = _make_order('RCBI1')
        registration = RTORegistration.objects.create(sales_order=order)
        self.rc_book_creation = _RCBookCreation.objects.create(rto_registration=registration)

    def test_create_with_no_item_rows(self):
        payload = {
            'rc_book_creation': self.rc_book_creation.pk, 'issue_type': 'customer',
            'items-TOTAL_FORMS': '0', 'items-INITIAL_FORMS': '0',
            'items-MIN_NUM_FORMS': '0', 'items-MAX_NUM_FORMS': '1000',
        }
        response = self.client.post(_reverse('rto:rc_book_issue_create'), payload)
        self.assertEqual(response.status_code, 302)


from accounts.models import CompanySettings as _CompanySettings
from masters.models import Supplier as _Supplier
from rto.models import NumberReceiptEntryCreation as _NumberReceiptEntryCreation


class NumberReceiptEntryCreationTaxTests(_TestCase):
    """rto.models.NumberReceiptEntryCreation.save() used to hardcode
    cgst=9/sgst=9 (an 18% flat rate baked into the field defaults) and never
    looked at CompanySettings or the customer's state. That silently
    produced the wrong tax total the moment the company's configured GST
    rate wasn't 9%/9%, or the customer was out-of-state (no IGST branch
    existed at all). Fixed by delegating to billing.models.split_gst(),
    same as every other tax-bearing module."""

    def setUp(self):
        settings_ = _CompanySettings.get_instance()
        settings_.cgst_rate = Decimal('6')
        settings_.sgst_rate = Decimal('6')
        settings_.state = 'Tamil Nadu'
        settings_.save()
        self.agent = _Supplier.objects.create(supplier_name='NumRec Agent Co')

    def _make_order_entry(self, customer_state):
        customer = Customer.objects.create(
            full_name='RTO Tax Customer', phone='9000000001', state=customer_state,
        )
        order = VehicleSalesOrder.objects.create(
            customer=customer, booking_amount=Decimal('1000'), total_amount=Decimal('100000'),
        )
        return _NumberOrderEntryCreation.objects.create(sales_order=order, agent=self.agent)

    def test_intrastate_uses_company_configured_rate_not_hardcoded_nine(self):
        order_entry = self._make_order_entry('Tamil Nadu')
        doc = _NumberReceiptEntryCreation.objects.create(
            order_entry=order_entry, agent=self.agent, rate=Decimal('1000'),
        )
        doc.refresh_from_db()
        # 6% + 6% = 12%, not the old hardcoded 9%+9%=18%
        self.assertEqual(doc.total, Decimal('1120.00'))
        self.assertEqual(doc.cgst_amount, Decimal('60.00'))
        self.assertEqual(doc.sgst_amount, Decimal('60.00'))
        self.assertEqual(doc.igst_amount, Decimal('0.00'))

    def test_interstate_customer_gets_igst_not_cgst_sgst(self):
        order_entry = self._make_order_entry('Karnataka')
        doc = _NumberReceiptEntryCreation.objects.create(
            order_entry=order_entry, agent=self.agent, rate=Decimal('1000'),
        )
        doc.refresh_from_db()
        # Company is Tamil Nadu, customer is Karnataka -> full 12% as IGST, same total
        self.assertEqual(doc.total, Decimal('1120.00'))
        self.assertEqual(doc.cgst_amount, Decimal('0.00'))
        self.assertEqual(doc.sgst_amount, Decimal('0.00'))
        self.assertEqual(doc.igst_amount, Decimal('120.00'))


from django.db.migrations.executor import MigrationExecutor
from django.db import connection
from django.test import TransactionTestCase


class BackfillRtoGstAmountsMigrationTests(TransactionTestCase):
    """0008_replace_hardcoded_gst_with_split_gst added cgst_amount/
    sgst_amount/igst_amount at default=0 and dropped the old cgst/sgst
    percent fields, with no data migration -- every pre-existing
    NumberReceiptEntryCreation row (many of them Submitted and therefore
    locked, per DocStatusMixin, so save() never runs again) would have
    permanently read 0 for all three GST amounts despite a real, nonzero
    total. Fixed by 0009_backfill_rto_gst_amounts, which runs *before*
    0010_remove_old_gst_percent_fields removes the old columns, so it can
    still read each row's actual historical cgst/sgst percentage and
    replicate the old pre-split_gst() formula (rate * pct / 100) instead of
    leaving zeros or guessing with today's company-configured rate."""

    # Squashing/optimizing later migrations could collapse this history and
    # break the executor-based replay below; if that ever happens, this test
    # needs to move to a fixture/data-only check instead.
    migrate_from = [('rto', '0007_alter_rchandover_vehicle_received')]
    migrate_to = [('rto', '0010_remove_old_gst_percent_fields')]

    def setUp(self):
        # customers/sales/masters aren't part of what's being tested here
        # (only the rto 0007 -> 0010 transition is) and the test DB is
        # already fully migrated for every app before this runs, so use the
        # real, current model classes for the unrelated FKs and only reach
        # for historical (pre-migration) models where the schema under test
        # actually differs -- rto.NumberReceiptEntryCreation's old cgst/sgst
        # percent fields.
        customer = Customer.objects.create(
            full_name='Migration Test Customer', phone='9000000099', state='Tamil Nadu',
        )
        order = VehicleSalesOrder.objects.create(
            customer=customer, booking_amount=Decimal('1000'), total_amount=Decimal('100000'),
        )
        agent = _Supplier.objects.create(supplier_name='Migration Test Agent')
        order_entry = _NumberOrderEntryCreation.objects.create(sales_order=order, agent=agent)

        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_from)
        old_apps = executor.loader.project_state(self.migrate_from).apps
        OldNumberReceiptEntryCreation = old_apps.get_model('rto', 'NumberReceiptEntryCreation')

        # Simulate a real historical Submitted document from before Task 2's
        # fix: cgst/sgst stored as percentages (not the new amount fields,
        # which don't exist yet at this point in history), total computed
        # with the old hardcoded-style formula.
        self.old_row_pk = OldNumberReceiptEntryCreation.objects.create(
            order_entry_id=order_entry.pk, agent_id=agent.pk, docstatus=1,
            rate=Decimal('500'), cgst=Decimal('9'), sgst=Decimal('9'), total=Decimal('590'),
        ).pk

        executor.loader.build_graph()
        executor.migrate(self.migrate_to)

    def test_backfill_produces_nonzero_gst_amounts_matching_historical_total(self):
        doc = _NumberReceiptEntryCreation.objects.get(pk=self.old_row_pk)
        self.assertEqual(doc.cgst_amount, Decimal('45.00'))
        self.assertEqual(doc.sgst_amount, Decimal('45.00'))
        self.assertEqual(doc.igst_amount, Decimal('0.00'))
        # The total field was never touched by the migration (docstatus=1
        # rows can't be re-saved) -- confirm the backfilled amounts actually
        # reconcile with it, i.e. rate + cgst_amount + sgst_amount == total.
        self.assertEqual(doc.rate + doc.cgst_amount + doc.sgst_amount + doc.igst_amount, doc.total)

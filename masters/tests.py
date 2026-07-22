"""
Regression tests for the Order Form Series batch-numbering generator
(Phase 8a) -- the numbering-series mechanism every downstream Sales Form/
RTO/Used-Vehicle document links to, and the ownership check on its own
cancel view (round-2 audit finding).
"""
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import Branch, Role, User
from masters.models import OrderFormSettings, OrderFormSeries


class OrderFormSeriesGenerateTests(TestCase):

    def setUp(self):
        self.branch = Branch.objects.create(branch_name='Main Branch')
        self.user = User.objects.create_superuser(username='mfg_admin', email='mfgadmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)

    def _configure(self, **overrides):
        instance = OrderFormSettings.get_instance()
        instance.new_vehicle = True
        instance.branch = self.branch
        instance.prefix = 'ORD-'
        instance.digits = 5
        instance.count = 3
        for k, v in overrides.items():
            setattr(instance, k, v)
        instance.save()
        return instance

    def test_generate_creates_the_right_count_correctly_numbered_and_submitted(self):
        self._configure()
        self.client.post(reverse('masters:order_form_settings_generate'))
        series = list(OrderFormSeries.objects.order_by('order_form_no'))
        self.assertEqual(len(series), 3)
        self.assertEqual([s.order_form_no for s in series], ['ORD-00001', 'ORD-00002', 'ORD-00003'])
        for s in series:
            self.assertEqual(s.docstatus, OrderFormSeries.DocStatus.SUBMITTED)
            self.assertEqual(s.status, 'unused')

    def test_second_generate_call_continues_from_the_previous_highest_with_no_collisions(self):
        self._configure()
        self.client.post(reverse('masters:order_form_settings_generate'))
        self.client.post(reverse('masters:order_form_settings_generate'))
        numbers = list(OrderFormSeries.objects.order_by('order_form_no').values_list('order_form_no', flat=True))
        self.assertEqual(len(numbers), 6)
        self.assertEqual(len(numbers), len(set(numbers)), f"duplicate order_form_no values: {numbers}")
        self.assertEqual(numbers[-1], 'ORD-00006')

    def test_generate_blocked_without_branch_prefix_or_count(self):
        instance = OrderFormSettings.get_instance()
        instance.new_vehicle = True
        instance.save()  # branch/prefix/count left unset
        self.client.post(reverse('masters:order_form_settings_generate'))
        self.assertEqual(OrderFormSeries.objects.count(), 0)


class OrderFormSeriesOwnershipTests(TestCase):
    """order_form_series_cancel -- no submit view exists (rows are
    auto-submitted at generation time), but cancel is still ownership-gated
    via created_by, per the round-2 audit fix."""

    def setUp(self):
        role, _ = Role.objects.get_or_create(role_name='Spares')
        self.branch = Branch.objects.create(branch_name='Second Branch')
        self.owner = User.objects.create_user(username='ofs_owner', email='ofsowner@example.com', password='Test-Pass-123!', role=role)
        self.other = User.objects.create_user(username='ofs_other', email='ofsother@example.com', password='Test-Pass-123!', role=role)
        self.series = OrderFormSeries.objects.create(
            order_form_no='ORD-90001', branch=self.branch, status='unused',
            docstatus=OrderFormSeries.DocStatus.SUBMITTED, created_by=self.owner,
        )

    def test_non_owner_cannot_cancel(self):
        self.client.force_login(self.other)
        response = self.client.post(reverse('masters:order_form_series_cancel', args=[self.series.pk]))
        self.assertEqual(response.status_code, 403)

    def test_owner_can_cancel(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse('masters:order_form_series_cancel', args=[self.series.pk]))
        self.assertEqual(response.status_code, 302)
        self.series.refresh_from_db()
        self.assertEqual(self.series.docstatus, OrderFormSeries.DocStatus.CANCELLED)


from masters.models import Supplier as _Supplier, Warehouse as _Warehouse


class SupplierCRUDTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser(username='sup_admin', email='supadmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)

    def test_create_then_detail_then_list(self):
        response = self.client.post(reverse('masters:supplier_create'), {
            'supplier_name': 'ACME Spares Pvt Ltd', 'country': 'India', 'supplier_type': 'company',
        })
        self.assertEqual(response.status_code, 302)
        supplier = _Supplier.objects.get(supplier_name='ACME Spares Pvt Ltd')

        response = self.client.get(reverse('masters:supplier_detail', args=[supplier.pk]))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse('masters:supplier_list'))
        self.assertEqual(response.status_code, 200)

    def test_default_currency_payment_terms_tax_id_fields_save(self):
        """Live re-check of the reference server's Supplier doctype (Pending
        Correction #2) found default_currency, payment_terms and tax_id as
        real fields not covered by the earlier 5-field fix."""
        response = self.client.post(reverse('masters:supplier_create'), {
            'supplier_name': 'Precision Parts Co', 'country': 'India', 'supplier_type': 'company',
            'default_currency': 'INR', 'payment_terms': 'Net 30', 'tax_id': 'ABCDE1234F',
        })
        self.assertEqual(response.status_code, 302)
        supplier = _Supplier.objects.get(supplier_name='Precision Parts Co')
        self.assertEqual(supplier.default_currency, 'INR')
        self.assertEqual(supplier.payment_terms, 'Net 30')
        self.assertEqual(supplier.tax_id, 'ABCDE1234F')

        from masters.forms import SupplierForm
        form = SupplierForm()
        self.assertIn('default_currency', form.fields)
        self.assertIn('payment_terms', form.fields)
        self.assertIn('tax_id', form.fields)


class WarehouseCRUDTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser(username='wh_admin', email='whadmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)

    def test_create_then_list(self):
        response = self.client.post(reverse('masters:warehouse_create'), {'name': 'Central Warehouse'})
        self.assertEqual(response.status_code, 302)
        warehouse = _Warehouse.objects.get(name='Central Warehouse')

        response = self.client.get(reverse('masters:warehouse_list'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(warehouse, response.context['warehouses'])


from masters.models import SparesCategory as _SparesCategory


class CategoryCRUDTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser(username='cat_admin', email='catadmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)

    def test_create_then_list(self):
        response = self.client.post(reverse('masters:category_create'), {'name': 'Engine Parts'})
        self.assertEqual(response.status_code, 302)
        category = _SparesCategory.objects.get(name='Engine Parts')
        response = self.client.get(reverse('masters:category_list'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(category, response.context['categories'])


class ModelAndPriceCRUDTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser(username='mp_admin', email='mpadmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)
        from customers.models import BikeModel
        self.bike_model = BikeModel.objects.create(brand='MP Brand', model_name='MP Model', ex_showroom_price=Decimal('100000'))

    def test_create_then_list(self):
        response = self.client.post(reverse('masters:model_and_price_create'), {'model_code': self.bike_model.pk})
        self.assertEqual(response.status_code, 302)
        from masters.models import ModelAndPrice
        self.assertTrue(ModelAndPrice.objects.filter(model_code=self.bike_model).exists())


class CustomerPriceCreateTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser(username='cp_admin', email='cpadmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)
        from customers.models import BikeModel
        self.bike_model = BikeModel.objects.create(brand='CP Brand2', model_name='CP Model2', ex_showroom_price=Decimal('90000'))

    def test_create_with_no_item_rows(self):
        payload = {
            'model_code': self.bike_model.pk,
            'items-TOTAL_FORMS': '0', 'items-INITIAL_FORMS': '0',
            'items-MIN_NUM_FORMS': '0', 'items-MAX_NUM_FORMS': '1000',
        }
        response = self.client.post(reverse('masters:customer_price_create'), payload)
        self.assertEqual(response.status_code, 302)
        from masters.models import CustomerPrice
        self.assertTrue(CustomerPrice.objects.filter(model_code=self.bike_model).exists())


class DealerPriceListCreateTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser(username='dpl_admin', email='dpladmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)
        from customers.models import Customer
        self.customer = Customer.objects.create(full_name='DPL Dealer', phone='9000000002')

    def test_create_with_no_item_rows(self):
        payload = {
            'dealer_name': self.customer.pk,
            'items-TOTAL_FORMS': '0', 'items-INITIAL_FORMS': '0',
            'items-MIN_NUM_FORMS': '0', 'items-MAX_NUM_FORMS': '1000',
        }
        response = self.client.post(reverse('masters:dealer_price_list_create'), payload)
        self.assertEqual(response.status_code, 302)
        from masters.models import DealerPriceList
        self.assertTrue(DealerPriceList.objects.filter(dealer_name=self.customer).exists())


class VehicleFittingSparesCreateTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser(username='vfs_admin', email='vfsadmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)
        from customers.models import BikeModel
        self.bike_model = BikeModel.objects.create(brand='VFS2', model_name='VFS2 Model', ex_showroom_price=Decimal('90000'))

    def test_create_with_no_item_rows(self):
        payload = {
            'vehicle': self.bike_model.pk,
            'items-TOTAL_FORMS': '0', 'items-INITIAL_FORMS': '0',
            'items-MIN_NUM_FORMS': '0', 'items-MAX_NUM_FORMS': '1000',
        }
        response = self.client.post(reverse('masters:vehicle_fitting_spares_create'), payload)
        self.assertEqual(response.status_code, 302)
        from masters.models import VehicleFittingSpares
        self.assertTrue(VehicleFittingSpares.objects.filter(vehicle=self.bike_model).exists())

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

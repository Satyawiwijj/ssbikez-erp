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

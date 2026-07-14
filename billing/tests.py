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

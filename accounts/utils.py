"""
Shared helpers used across apps. Currently one function: summing a
document's child-table line items back into a parent total field — the
one place this logic lives, so Sales Order, Invoice, and Vehicle Delivery
(and any future document with priced line items) all compute totals the
same way instead of three near-identical, independently-drifting copies.
"""
from decimal import Decimal


def recompute_total_from_items(parent, related_name, amount_field):
    """Sum `amount_field` across `parent`'s `related_name` relation.

    Does not save `parent` — the caller decides what to do with the
    result (some documents, like Invoice, need to cascade the new total
    into other derived fields like GST and final_amount before saving).
    """
    items = getattr(parent, related_name).all()
    total = Decimal('0')
    for item in items:
        total += getattr(item, amount_field) or Decimal('0')
    return total

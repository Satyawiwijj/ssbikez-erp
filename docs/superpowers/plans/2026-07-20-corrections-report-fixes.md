# SS Bikez Corrections Report — Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close every item in the client's `SSBikez_Corrections_Report_Final.pdf` (dated 2026-07-17 — 3 pending + 11 new issues) with a real, evidence-backed code fix, tested and committed one item at a time — not another round of "confirmed working" claims the client has already rejected twice.

**Architecture:** Each of the client's 14 reported items was independently reproduced or disproven against the actual codebase before this plan was written (not assumed from the report text alone) — see the "What was actually found" line in each task. Several items turned out to share one root cause (three different document types independently re-implementing "sum child-table lines into a parent total," nine call sites sharing one dead-end error page), so those are fixed once via a shared pattern and applied per document type, rather than four/nine near-duplicate patches.

**Tech Stack:** Django 6.0.7 / Python 3.12, existing app structure (`sales`, `billing`, `rto`, `spares`, `accounts`, `masters`).

## Global Constraints

- Every fix follows TDD: failing test first (Django `TestCase`), then the minimal fix, then green, then commit.
- No `Co-Authored-By: Claude` (or any AI-authorship) trailer in any commit message — standing project requirement.
- This app's document lifecycle is `Draft → Submitted → Cancelled → Amended` (`accounts.models.DocStatusMixin`) — any fix touching a submittable document (Sales Order, Invoice, Delivery) must respect this; never allow editing a Submitted document outside the existing Cancel-and-Amend path.
- GST/tax calculation must go through `billing.models.split_gst(gst_amount, customer=None)` — the one function in this codebase that correctly uses `CompanySettings`' configured CGST/SGST rates and applies IGST when the customer's state differs from the company's. Do not hand-roll tax math in any app.
- Full regression floor, must stay green throughout: `python manage.py test` (151 tests as of the last audit pass) and `python manage.py test e2e` (Playwright, 9 tests).
- This plan is independent of, and does not duplicate, the in-progress reference-server parity audit (Tiers 3-8, tracked separately in this session's task list) — items 9 and 10 of the client's "New Corrections" ("fields... functionalities are not working as expected" / "should match the standard ERP workflow wherever applicable") are general restatements of that audit's own goal and are addressed by continuing it, not by a task in this plan.

---

## File Structure

| File | Purpose |
|---|---|
| `templates/base.html` (modify) | Search bar: make the magnifying-glass icon an actual submit control. |
| `rto/models.py` (modify) | Replace hardcoded 9%/9% CGST/SGST defaults with `split_gst()`. |
| `accounts/utils.py` (new) | Shared `recompute_total_from_items()` helper — the one place "sum child rows into a parent total field" is implemented. |
| `sales/models.py` (modify) | `VehicleSalesOrder.recompute_totals()`, `VehicleDelivery.recompute_totals()`, `VehicleSalesOrder.total_amount_across_invoices` property. |
| `sales/forms.py` (modify) | `total_amount` no longer required from the user on `VehicleSalesOrderForm` (mirrors the existing `InvoiceForm` pattern for derived fields). |
| `sales/views.py` (modify) | Call `recompute_totals()` after `items_formset.save()` in `order_create`/`order_update`/`delivery_create`/`delivery_update`; use `order_detail`'s multi-invoice total in the template context. |
| `billing/models.py` (modify) | `Invoice.recompute_totals()`. |
| `billing/views.py` (modify) | Call `recompute_totals()` in `invoice_create`/`invoice_update`. |
| `billing/_gap14_31_views.py` (modify) | `general_ledger` gets date-range + account filters and a `@require_module_action('finance', 'view')` gate; same gate added to `journal_entry_detail`. |
| `templates/billing/general_ledger.html` (modify) | Filter form (date range, account dropdown). |
| `accounts/views.py` (modify) | New shared `submitted_document_locked(request, redirect_url)` helper replacing the 9 bare `HttpResponseForbidden` calls. |
| `billing/views.py`, `sales/views.py`, `vas/views.py` (modify) | Replace all 9 bare 403 strings with the shared helper. |
| `templates/accounts/submitted_locked.html` (new) | The proper error page with a working "Cancel & Amend" link. |
| `masters/forms.py` (modify, if a gap is found) | Any Supplier field found missing after live re-verification (Task 10). |
| `reference_erp_spec/tools/check_supplier_fields.py` (new) | One-shot live re-check of the reference server's actual Supplier doctype (the original bulk extraction failed for this one doctype). |
| `accounts/models.py` or a small migration (modify, if Task 11 confirms) | Hide "Purchase Estimation" from the default sidebar nav. |

---

## Task 1: Search bar — the magnifying-glass icon doesn't submit

**What was actually found:** the search backend (`accounts/views.py:744` `global_search`) works correctly — verified by hitting it directly with the Django test client (200 OK, real results for customers/vehicles/enquiries/orders/job cards/spares). The bug is in the UI: `templates/base.html:758-767` renders a real `<form method="get" action="{% url 'accounts:search' %}">` with a text `<input>`, but the search icon (`<i class="fas fa-search">`, line 760) is a purely decorative element with no click handler and is not a `<button type="submit">`. Pressing Enter submits the form (native browser behavior); clicking the icon — the only visible affordance that looks clickable — does nothing. This is a fully plausible, evidence-backed explanation for "search is still not working" surviving multiple "confirmed working" rounds: those rounds tested that the backend returns correct results, never that a user could actually trigger a search by clicking the thing that looks like the search trigger.

**Files:**
- Modify: `templates/base.html:758-767`
- Test: `e2e/test_search_bar.py` (new)

- [ ] **Step 1: Write the failing e2e test**

Create `e2e/test_search_bar.py`:

```python
from e2e.base import PlaywrightTestCase
from e2e.fixtures import make_branch
from accounts.models import Role
from customers.models import Customer


class SearchBarClickTests(PlaywrightTestCase):

    def setUp(self):
        super().setUp()
        role = Role.objects.create(role_name='Managing Director')
        branch = make_branch()
        self.user = self.make_user('search_e2e_admin', role=role, branch=branch, is_superuser=True)
        Customer.objects.create(full_name='Findable Customer Search', phone='9998887770')

    def test_clicking_the_search_icon_submits_the_search(self):
        self.login_as(self.user)
        self.goto('/accounts/dashboard/')
        self.page.fill('#topbar-search-input', 'Findable Customer Search')
        # Click the magnifying-glass icon itself, not press Enter — this is
        # the exact interaction the client's report says doesn't work.
        self.page.click('.topbar form i.fa-search')
        self.page.wait_for_url('**/accounts/search/**')
        assert 'Findable Customer Search' in self.page.content()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python manage.py test e2e.test_search_bar -v 2`
Expected: FAIL — clicking the icon does not navigate to the search results page (the URL stays on `/accounts/dashboard/`, `wait_for_url` times out).

- [ ] **Step 3: Fix the template**

In `templates/base.html`, replace lines 758-767:

```html
  <form method="get" action="{% url 'accounts:search' %}" style="flex:1; max-width:320px; margin: 0 12px;">
    <div style="position:relative;">
      <button type="submit" aria-label="Search"
              style="position:absolute;left:6px;top:50%;transform:translateY(-50%);background:none;border:none;padding:4px;cursor:pointer;color:#6B7280;font-size:13px;">
        <i class="fas fa-search"></i>
      </button>
      <input type="text" name="q" value="{{ request.GET.q|default:'' }}" placeholder="Search…"
             id="topbar-search-input"
             data-on-search-page="{% if request.resolver_match.url_name == 'search' %}1{% endif %}"
             style="padding-left:32px;width:100%;border-radius:8px;border:1px solid #e5e7eb;font-size:13px;height:36px;background:#f9fafb;">
    </div>
  </form>
```

(Only change: the decorative `<i>` is now wrapped in a real `<button type="submit">`, keeping the same icon/visual position. The existing "clear box → go to dashboard" JS immediately below, lines 769-777, is unchanged and still applies.)

- [ ] **Step 4: Run it to verify it passes**

Run: `python manage.py test e2e.test_search_bar -v 2`
Expected: PASS.

- [ ] **Step 5: Run the full e2e suite to confirm no regression**

Run: `python manage.py test e2e`
Expected: all e2e tests pass (10 now, was 9).

- [ ] **Step 6: Commit**

```bash
git add templates/base.html e2e/test_search_bar.py
git commit -m "fix: make the topbar search icon an actual submit button, not decoration"
```

---

## Task 2: Tax calculation isn't centralized — RTO hardcodes 9%/9%, ignores company rates and IGST

**What was actually found:** `billing.models.split_gst()` (verified in an earlier audit pass) correctly reads `CompanySettings.cgst_rate`/`sgst_rate` and applies IGST for interstate customers — but a repo-wide grep shows only `billing/pdf_views.py`, `billing/views.py`, and `service/views.py` actually call it. `rto/models.py:434-435` defines its own `cgst`/`sgst` fields with **hardcoded `default=9`** (i.e. a fixed 18% total baked into the field definition, not read from `CompanySettings`), and `rto/models.py:441` computes `self.total = rate + (rate * (self.cgst or 0) / 100) + (rate * (self.sgst or 0) / 100)` — no IGST branch at all. This is a precise, direct match for "Tax table values are not calculating across all modules": if the company's actual configured GST rate isn't 9%/9%, or the customer is out-of-state, RTO's tax table is simply wrong, silently.

**Files:**
- Modify: `rto/models.py` (the model containing the `cgst`/`sgst`/`total` fields at lines 434-441 — read the file to confirm the exact class name before editing, it wasn't fully captured during planning)
- Test: `rto/tests.py`

- [ ] **Step 1: Identify the exact model and read full context**

Run: `grep -n "cgst\s*=\s*models" rto/models.py` to get the line, then read 40 lines of context around it to find the enclosing `class` name and how `total` is invoked (property vs. method vs. signal).

- [ ] **Step 2: Write the failing test**

(Uses the real class/field names found in Step 1 — replace `RTODocumentClassName` below with the actual class name before writing this test.)

```python
from decimal import Decimal
from django.test import TestCase
from accounts.models import CompanySettings
from customers.models import Customer
# from rto.models import RTODocumentClassName  # use the real name found in Step 1


class RTOTaxUsesCompanyRatesTests(TestCase):

    def setUp(self):
        settings_ = CompanySettings.get_instance()
        settings_.cgst_rate = Decimal('6')
        settings_.sgst_rate = Decimal('6')
        settings_.state = 'Tamil Nadu'
        settings_.save()

    def test_intrastate_uses_company_configured_rate_not_hardcoded_nine(self):
        customer = Customer.objects.create(full_name='RTO Tax Customer', phone='9000000001', state='Tamil Nadu')
        # Construct the RTO document exactly as the real class requires
        # (fill in the real required fields found in Step 1).
        doc = RTODocumentClassName.objects.create(
            customer=customer,
            rate=Decimal('1000'),
        )
        doc.refresh_from_db()
        # 6% + 6% = 12%, not the old hardcoded 9%+9%=18%
        self.assertEqual(doc.total, Decimal('1120.00'))

    def test_interstate_customer_gets_igst_not_cgst_sgst(self):
        customer = Customer.objects.create(full_name='RTO IGST Customer', phone='9000000002', state='Karnataka')
        doc = RTODocumentClassName.objects.create(
            customer=customer,
            rate=Decimal('1000'),
        )
        doc.refresh_from_db()
        # Company is Tamil Nadu, customer is Karnataka -> full 12% as IGST, same total
        self.assertEqual(doc.total, Decimal('1120.00'))
```

- [ ] **Step 3: Run it to verify it fails**

Run: `python manage.py test rto.tests.RTOTaxUsesCompanyRatesTests -v 2`
Expected: FAIL — with the hardcoded `cgst=9, sgst=9` defaults, `doc.total` comes out to `1180.00` (18%), not `1120.00` (12%), for both tests (the interstate test fails for the same reason, since there's currently no IGST branch at all).

- [ ] **Step 4: Fix the model**

Replace the hardcoded fields and `total` calculation (exact lines depend on Step 1's findings) with a call to `split_gst`:

```python
    def save(self, *args, **kwargs):
        from billing.models import split_gst
        from decimal import Decimal
        rate = self.rate or Decimal('0')
        cgst_amt, sgst_amt, igst_amt = split_gst(
            (rate * Decimal('12') / Decimal('100')).quantize(Decimal('0.01')),
            customer=self.customer,
        )
        # Adjust this block to whatever the real field names from Step 1 are —
        # this shows the pattern (delegate to split_gst, never hand-roll rates).
        self.cgst_amount = cgst_amt
        self.sgst_amount = sgst_amt
        self.igst_amount = igst_amt
        self.total = rate + cgst_amt + sgst_amt + igst_amt
        super().save(*args, **kwargs)
```

Remove the old hardcoded `cgst = models.DecimalField(..., default=9, ...)` / `sgst = models.DecimalField(..., default=9, ...)` fields (or repurpose them as computed/read-only display fields if other code reads them directly — check with `grep -rn "\.cgst\b\|\.sgst\b" rto/` before deleting). If removing fields, this needs a migration:

```bash
python manage.py makemigrations rto -n replace_hardcoded_gst_with_split_gst
```

- [ ] **Step 5: Run it to verify it passes**

Run: `python manage.py test rto.tests.RTOTaxUsesCompanyRatesTests -v 2`
Expected: PASS.

- [ ] **Step 6: Run the full rto suite**

Run: `python manage.py test rto`
Expected: all pass, no regressions from removing/renaming the old fields (check templates and any other reader of `.cgst`/`.sgst` found in Step 4's grep — update them to the new field names too, in this same task, not left dangling).

- [ ] **Step 7: Commit**

```bash
git add rto/models.py rto/migrations/ rto/tests.py
git commit -m "fix: RTO tax calculation now uses company-configured GST rates and IGST, not a hardcoded 9%/9%"
```

---

## Task 3: Shared "recompute parent total from line items" helper

**What was actually found:** this is the shared root cause behind three of the client's "amount calculation" complaints (New #1, #3, #4). `sales/views.py` (`order_create`/`order_update`, lines 601-650), `sales/views.py` (`delivery_create`/`delivery_update`, lines 762-815), and `billing/views.py` (`invoice_create`/`invoice_update`, lines 105-148) all follow the identical pattern: save the parent form and its child-item formset **completely independently** — nothing ever sums `VehicleSaleItem.amount`, `InvoiceItem.total`, or `DeliveryNoteItem.actual_amount` back into the parent's `total_amount`/`subtotal` field. A user adds priced line items; the parent total field stays whatever was typed (or its default) and never reflects them. Confirmed by reading every one of these six view functions directly, not inferred.

**Files:**
- Create: `accounts/utils.py`
- Test: `accounts/tests.py`

**Interfaces:**
- Produces: `recompute_total_from_items(parent, related_name, amount_field) -> Decimal` — sums `getattr(item, amount_field)` across `getattr(parent, related_name).all()` and returns the sum (does not save; caller decides what to do with it, since Invoice needs extra cascading logic — see Task 5).

- [ ] **Step 1: Write the failing test**

Add to `accounts/tests.py`:

```python
from decimal import Decimal as _Decimal


class RecomputeTotalFromItemsTests(TestCase):

    def test_sums_the_amount_field_across_related_items(self):
        from sales.models import VehicleSalesOrder, VehicleSaleItem
        from customers.models import Customer
        from accounts.utils import recompute_total_from_items

        customer = Customer.objects.create(full_name='Recompute Test Customer', phone='9000000010')
        order = VehicleSalesOrder.objects.create(customer=customer, booking_amount=_Decimal('1000'), total_amount=_Decimal('0'))
        VehicleSaleItem.objects.create(sales_order=order, item_name='Helmet', rate=_Decimal('500'), quantity=1, amount=_Decimal('500'))
        VehicleSaleItem.objects.create(sales_order=order, item_name='Accessories', rate=_Decimal('300'), quantity=2, amount=_Decimal('600'))

        total = recompute_total_from_items(order, 'items', 'amount')

        self.assertEqual(total, _Decimal('1100'))

    def test_returns_zero_for_no_items(self):
        from sales.models import VehicleSalesOrder
        from customers.models import Customer
        from accounts.utils import recompute_total_from_items

        customer = Customer.objects.create(full_name='Recompute Empty Customer', phone='9000000011')
        order = VehicleSalesOrder.objects.create(customer=customer, booking_amount=_Decimal('1000'), total_amount=_Decimal('0'))

        total = recompute_total_from_items(order, 'items', 'amount')

        self.assertEqual(total, _Decimal('0'))
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python manage.py test accounts.tests.RecomputeTotalFromItemsTests -v 2`
Expected: FAIL with `ModuleNotFoundError: No module named 'accounts.utils'` (or `ImportError`).

- [ ] **Step 3: Create the helper**

Create `accounts/utils.py`:

```python
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
```

- [ ] **Step 4: Run it to verify it passes**

Run: `python manage.py test accounts.tests.RecomputeTotalFromItemsTests -v 2`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add accounts/utils.py accounts/tests.py
git commit -m "feat: add shared recompute_total_from_items helper"
```

---

## Task 4: Apply the helper to Sales Order (New Correction #1)

**Files:**
- Modify: `sales/models.py` (add `VehicleSalesOrder.recompute_totals`, near the existing `current_delivery`/`current_invoice` properties around line 484)
- Modify: `sales/forms.py:190` (`total_amount` field — make it not required from the user, matching how `InvoiceForm` already treats its derived fields)
- Modify: `sales/views.py` (`order_create` lines 601-619, `order_update` lines 643-655)
- Test: `sales/tests.py`

**Interfaces:**
- Consumes: `accounts.utils.recompute_total_from_items` (Task 3)
- Produces: `VehicleSalesOrder.recompute_totals()` — sums `self.items` (`VehicleSaleItem.amount`), sets `self.total_amount`, saves with `update_fields=['total_amount']`.

- [ ] **Step 1: Write the failing test**

Add to `sales/tests.py`:

```python
class SalesOrderTotalRecomputeTests(TestCase):

    def setUp(self):
        from customers.models import Customer
        self.customer = Customer.objects.create(full_name='Order Total Customer', phone='9000000020')

    def test_total_amount_reflects_summed_line_items_after_create(self):
        from django.test import Client
        from django.urls import reverse
        from accounts.models import User

        user = User.objects.create_superuser(username='order_total_admin', email='ordertotal@example.com', password='Test-Pass-123!')
        client = Client()
        client.force_login(user)

        response = client.post(reverse('sales:order_create'), {
            'customer': self.customer.pk, 'booking_amount': '1000', 'discount_amount': '0',
            'items-TOTAL_FORMS': '2', 'items-INITIAL_FORMS': '0',
            'items-MIN_NUM_FORMS': '0', 'items-MAX_NUM_FORMS': '1000',
            'items-0-item_name': 'Helmet', 'items-0-rate': '500', 'items-0-quantity': '1', 'items-0-amount': '500',
            'items-1-item_name': 'Accessories', 'items-1-rate': '300', 'items-1-quantity': '2', 'items-1-amount': '600',
            'additional_fittings-TOTAL_FORMS': '0', 'additional_fittings-INITIAL_FORMS': '0',
            'additional_fittings-MIN_NUM_FORMS': '0', 'additional_fittings-MAX_NUM_FORMS': '1000',
            'advance_payments-TOTAL_FORMS': '0', 'advance_payments-INITIAL_FORMS': '0',
            'advance_payments-MIN_NUM_FORMS': '0', 'advance_payments-MAX_NUM_FORMS': '1000',
        })
        self.assertEqual(response.status_code, 302)

        from sales.models import VehicleSalesOrder
        order = VehicleSalesOrder.objects.get(customer=self.customer)
        self.assertEqual(order.total_amount, Decimal('1100'))
```

(`Decimal` is the existing `from decimal import Decimal` import already at the top of `sales/tests.py` — confirm it exists before using; add it if not. Note: unlike `billing/tests.py`, `sales/tests.py` does NOT alias this import as `_Decimal` — use the plain name here.)

- [ ] **Step 2: Run it to verify it fails**

Run: `python manage.py test sales.tests.SalesOrderTotalRecomputeTests -v 2`
Expected: FAIL — `order.total_amount` is `0` (or whatever default), not `1100`, because nothing recomputes it from the items formset today.

- [ ] **Step 3: Add the model method**

In `sales/models.py`, add directly below the existing `current_invoice` property (around line 492):

```python
    def recompute_totals(self):
        """Sum VehicleSaleItem.amount across this order's items and persist
        into total_amount. Called after the items formset is saved — see
        sales/views.py order_create/order_update."""
        from accounts.utils import recompute_total_from_items
        self.total_amount = recompute_total_from_items(self, 'items', 'amount')
        self.save(update_fields=['total_amount'])
```

- [ ] **Step 4: Make total_amount not required from the user**

In `sales/forms.py`, in `VehicleSalesOrderForm.__init__` (after the existing `super().__init__` call, around line 195 — read the file first to place this correctly alongside any other `__init__` logic already there):

```python
        # total_amount is always derived from the items formset in the view
        # (VehicleSalesOrder.recompute_totals) — same pattern InvoiceForm
        # already uses for gst_amount/final_amount. Don't force the user to
        # guess a number before the items formset has even been saved.
        self.fields['total_amount'].required = False
```

- [ ] **Step 5: Call recompute_totals() in the views**

In `sales/views.py`, `order_create` (after `items_formset.save()`, currently line 612):

```python
            items_formset.instance = order
            items_formset.save()
            order.recompute_totals()
```

And in `order_update` (after `items_formset.save()`, currently line 650):

```python
            items_formset.save()
            order.recompute_totals()
```

- [ ] **Step 6: Run it to verify it passes**

Run: `python manage.py test sales.tests.SalesOrderTotalRecomputeTests -v 2`
Expected: PASS.

- [ ] **Step 7: Run the full sales suite**

Run: `python manage.py test sales`
Expected: all pass, no regressions (in particular, confirm no existing test relied on `total_amount` being exactly what was posted in the form — if one does and it's testing real behavior, that test's expectation was itself wrong and should be updated to expect the recomputed value; if it was asserting the bug, note this in the commit).

- [ ] **Step 8: Commit**

```bash
git add sales/models.py sales/forms.py sales/views.py sales/tests.py
git commit -m "fix: Sales Order total_amount now recomputed from line items, not manually typed"
```

---

## Task 5: Apply the helper to Invoice (New Correction #4)

**What was actually found:** `InvoiceForm.clean()` (`billing/forms.py:33-58`) already correctly cascades `gst_amount` and `final_amount` FROM `subtotal` — that part works. The actual gap is one level up: nothing computes `subtotal` itself from `InvoiceItem.total`. `subtotal` is just a plain user-typed field.

**Files:**
- Modify: `billing/models.py` (add `Invoice.recompute_totals`, near `post_journal_entry` around line 137)
- Modify: `billing/views.py` (`invoice_create` lines 105-119, `invoice_update` lines 127-148)
- Test: `billing/tests.py`

**Interfaces:**
- Consumes: `accounts.utils.recompute_total_from_items` (Task 3)
- Produces: `Invoice.recompute_totals()` — sums `self.items` (`InvoiceItem.total`), sets `self.subtotal`, re-derives `gst_amount` (18% default, or company rate — mirror `InvoiceForm.clean()`'s exact formula so the two never drift apart) and `final_amount`, saves.

- [ ] **Step 1: Write the failing test**

Add to `billing/tests.py`:

```python
class InvoiceSubtotalRecomputeTests(_TestCase):

    def setUp(self):
        self.user = _User.objects.create_superuser(username='inv_recalc_admin', email='invrecalc@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)

    def test_subtotal_reflects_summed_line_items_after_create(self):
        order = _make_order('INVRECALC1')
        response = self.client.post(_reverse('billing:invoice_create'), {
            'sales_order': order.pk, 'invoice_number': 'RECALC-INV-0001',
            'subtotal': '0', 'discount_amount': '0',
            'invoice_date': '2026-08-01', 'status': 'unpaid',
            'items-TOTAL_FORMS': '2', 'items-INITIAL_FORMS': '0',
            'items-MIN_NUM_FORMS': '0', 'items-MAX_NUM_FORMS': '1000',
            'items-0-item_code': 'ENGINE-OIL', 'items-0-rate': '400', 'items-0-discount': '0', 'items-0-total': '400',
            'items-1-item_code': 'BRAKE-PAD', 'items-1-rate': '600', 'items-1-discount': '0', 'items-1-total': '600',
        })
        self.assertEqual(response.status_code, 302)
        from billing.models import Invoice
        invoice = Invoice.objects.get(invoice_number='RECALC-INV-0001')
        self.assertEqual(invoice.subtotal, _Decimal('1000'))
        self.assertEqual(invoice.final_amount, invoice.subtotal + invoice.gst_amount)
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python manage.py test billing.tests.InvoiceSubtotalRecomputeTests -v 2`
Expected: FAIL — `invoice.subtotal` is `0` (whatever was posted), not `1000`.

- [ ] **Step 3: Add the model method**

In `billing/models.py`, add directly below `post_journal_entry` (after the block added in the earlier GL-reversal fix, so after `reverse_journal_entry`):

```python
    def recompute_totals(self):
        """Sum InvoiceItem.total across this invoice's items and re-derive
        subtotal/gst_amount/final_amount from the result — mirrors the
        InvoiceForm.clean() cascade formula exactly so the two paths never
        disagree. Called after the items formset is saved — see
        billing/views.py invoice_create/invoice_update."""
        from decimal import Decimal
        from accounts.models import CompanySettings
        from accounts.utils import recompute_total_from_items

        self.subtotal = recompute_total_from_items(self, 'items', 'total')
        if self.subtotal > Decimal('0'):
            try:
                rate = Decimal(str(CompanySettings.get_instance().gst_rate or 18))
            except Exception:
                rate = Decimal('18')
            self.gst_amount = (self.subtotal * rate / Decimal('100')).quantize(Decimal('0.01'))
        else:
            self.gst_amount = Decimal('0')
        self.final_amount = self.subtotal + self.gst_amount - (self.discount_amount or Decimal('0'))
        self.save(update_fields=['subtotal', 'gst_amount', 'final_amount'])
```

- [ ] **Step 4: Call recompute_totals() in the views**

In `billing/views.py`, `invoice_create` (after `items_formset.save()`, currently line 115):

```python
            items_formset.instance = invoice
            items_formset.save()
            invoice.recompute_totals()
```

And in `invoice_update` (after `items_formset.save()`, currently line 141):

```python
            items_formset.save()
            invoice.recompute_totals()
```

- [ ] **Step 5: Run it to verify it passes**

Run: `python manage.py test billing.tests.InvoiceSubtotalRecomputeTests -v 2`
Expected: PASS.

- [ ] **Step 6: Run the full billing suite**

Run: `python manage.py test billing`
Expected: all pass (including the two GL-reversal tests from the earlier audit pass and the payment-reconciliation test — confirm no interaction, since `recompute_totals` only touches `subtotal`/`gst_amount`/`final_amount`, not the GL-posting fields).

- [ ] **Step 7: Commit**

```bash
git add billing/models.py billing/views.py billing/tests.py
git commit -m "fix: Invoice subtotal/GST/final_amount now recomputed from line items on create/update"
```

---

## Task 6: Apply the helper to Vehicle Delivery (New Correction #3)

**Files:**
- Modify: `sales/models.py` (add `VehicleDelivery.recompute_totals`, near the class's `__str__` around line 560)
- Modify: `sales/views.py` (`delivery_create` lines 762-781, `delivery_update` lines 799-815)
- Test: `sales/tests.py`

**Interfaces:**
- Consumes: `accounts.utils.recompute_total_from_items` (Task 3)
- Produces: `VehicleDelivery.recompute_totals()` — sums `self.items` (`DeliveryNoteItem.actual_amount`), sets `self.total_amount`, saves.

- [ ] **Step 1: Write the failing test**

Add to `sales/tests.py`:

```python
class VehicleDeliveryTotalRecomputeTests(TestCase):

    def test_total_amount_reflects_summed_delivery_items(self):
        from customers.models import Customer
        from sales.models import VehicleSalesOrder, VehicleDelivery, DeliveryNoteItem

        customer = Customer.objects.create(full_name='Delivery Total Customer', phone='9000000030')
        order = VehicleSalesOrder.objects.create(customer=customer, booking_amount=Decimal('1000'), total_amount=Decimal('50000'))
        delivery = VehicleDelivery.objects.create(sales_order=order, delivery_date='2026-08-01', total_amount=Decimal('0'))
        DeliveryNoteItem.objects.create(delivery=delivery, item_code='HELMET', rate=Decimal('500'), actual_amount=Decimal('500'))
        DeliveryNoteItem.objects.create(delivery=delivery, item_code='ACCESSORY-KIT', rate=Decimal('750'), actual_amount=Decimal('750'))

        delivery.recompute_totals()

        delivery.refresh_from_db()
        self.assertEqual(delivery.total_amount, Decimal('1250'))
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python manage.py test sales.tests.VehicleDeliveryTotalRecomputeTests -v 2`
Expected: FAIL with `AttributeError: 'VehicleDelivery' object has no attribute 'recompute_totals'`.

- [ ] **Step 3: Add the model method**

In `sales/models.py`, add directly below `VehicleDelivery.__str__` (around line 561):

```python
    def recompute_totals(self):
        """Sum DeliveryNoteItem.actual_amount across this delivery's items
        and persist into total_amount. Called after the items formset is
        saved — see sales/views.py delivery_create/delivery_update."""
        from accounts.utils import recompute_total_from_items
        self.total_amount = recompute_total_from_items(self, 'items', 'actual_amount')
        self.save(update_fields=['total_amount'])
```

- [ ] **Step 4: Call recompute_totals() in the views**

In `sales/views.py`, `delivery_create` (after `items_formset.save()`, currently line 770):

```python
            items_formset.instance = delivery
            items_formset.save()
            delivery.recompute_totals()
```

And in `delivery_update` (after `items_formset.save()`, currently line 806):

```python
            items_formset.save()
            delivery.recompute_totals()
```

- [ ] **Step 5: Run it to verify it passes**

Run: `python manage.py test sales.tests.VehicleDeliveryTotalRecomputeTests -v 2`
Expected: PASS.

- [ ] **Step 6: Run the full sales suite**

Run: `python manage.py test sales`
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add sales/models.py sales/views.py sales/tests.py
git commit -m "fix: Vehicle Delivery total_amount now recomputed from delivery line items"
```

---

## Task 7: Order detail should aggregate amounts across ALL related invoices (New Correction #5)

**What was actually found:** `VehicleSalesOrder.current_invoice` (`sales/models.py:489-492`) returns only the single most-recent non-cancelled invoice for an order. If an order legitimately has more than one active invoice (e.g. a supplementary/extras invoice issued after the main one), `order_detail` (`sales/views.py:531-541`) only ever shows that one invoice's amount — never a sum across all of them. This matches the client's literal request: "amounts should be fetched from all the related invoices."

**Files:**
- Modify: `sales/models.py` (add `VehicleSalesOrder.total_invoiced_amount` property, near `current_invoice`)
- Modify: `sales/views.py:531-541` (`order_detail` — pass the new total into the template context)
- Modify: `templates/sales/order_detail.html` (display the aggregated total alongside the existing single-invoice display — read the template first to find the right spot, don't guess a line number)
- Test: `sales/tests.py`

**Interfaces:**
- Produces: `VehicleSalesOrder.total_invoiced_amount` (property) — sums `final_amount` across every non-cancelled invoice on `self.invoices`.

- [ ] **Step 1: Write the failing test**

Add to `sales/tests.py`:

```python
class OrderTotalInvoicedAcrossInvoicesTests(TestCase):

    def test_sums_final_amount_across_all_non_cancelled_invoices(self):
        from customers.models import Customer
        from sales.models import VehicleSalesOrder
        from billing.models import Invoice

        customer = Customer.objects.create(full_name='Multi Invoice Customer', phone='9000000040')
        order = VehicleSalesOrder.objects.create(customer=customer, booking_amount=Decimal('1000'), total_amount=Decimal('80000'))
        Invoice.objects.create(sales_order=order, invoice_number='MULTI-INV-0001', subtotal=Decimal('50000'), final_amount=Decimal('50000'), invoice_date='2026-08-01')
        Invoice.objects.create(sales_order=order, invoice_number='MULTI-INV-0002', subtotal=Decimal('5000'), final_amount=Decimal('5000'), invoice_date='2026-08-05')

        self.assertEqual(order.total_invoiced_amount, Decimal('55000'))

    def test_excludes_cancelled_invoices(self):
        from customers.models import Customer
        from accounts.models import User
        from sales.models import VehicleSalesOrder
        from billing.models import Invoice

        customer = Customer.objects.create(full_name='Cancelled Invoice Customer', phone='9000000041')
        order = VehicleSalesOrder.objects.create(customer=customer, booking_amount=Decimal('1000'), total_amount=Decimal('50000'))
        user = User.objects.create_superuser(username='cancel_invoiced_admin', email='cancelinvoiced@example.com', password='Test-Pass-123!')
        inv = Invoice.objects.create(sales_order=order, invoice_number='CANCELLED-INV-0001', subtotal=Decimal('50000'), final_amount=Decimal('50000'), invoice_date='2026-08-01')
        inv.submit(user)
        inv.cancel(user)

        self.assertEqual(order.total_invoiced_amount, Decimal('0'))
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python manage.py test sales.tests.OrderTotalInvoicedAcrossInvoicesTests -v 2`
Expected: FAIL with `AttributeError: 'VehicleSalesOrder' object has no attribute 'total_invoiced_amount'`.

- [ ] **Step 3: Add the property**

In `sales/models.py`, directly below `current_invoice` (around line 492):

```python
    @property
    def total_invoiced_amount(self):
        """Sum of final_amount across every non-cancelled invoice on this
        order — unlike current_invoice (the single latest one), this is
        the real total when an order has more than one active invoice
        (e.g. a main invoice plus a later supplementary one)."""
        from decimal import Decimal
        from accounts.models import DocStatusMixin
        total = Decimal('0')
        for invoice in self.invoices.exclude(docstatus=DocStatusMixin.DocStatus.CANCELLED):
            total += invoice.final_amount or Decimal('0')
        return total
```

- [ ] **Step 4: Run it to verify it passes**

Run: `python manage.py test sales.tests.OrderTotalInvoicedAcrossInvoicesTests -v 2`
Expected: PASS.

- [ ] **Step 5: Wire it into order_detail**

Read `sales/views.py:531-560` (`order_detail`) and `templates/sales/order_detail.html` to find where `invoice` (the single `current_invoice`) is currently displayed. Add `'total_invoiced_amount': order.total_invoiced_amount` to the context dict returned by `order_detail`, and add a line near the existing invoice amount display in the template:

```html
<div class="detail-row">
  <span class="detail-label">Total Invoiced (all invoices)</span>
  <span class="detail-value">₹{{ total_invoiced_amount|floatformat:2 }}</span>
</div>
```

- [ ] **Step 6: Run the full sales suite**

Run: `python manage.py test sales`
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add sales/models.py sales/views.py templates/sales/order_detail.html sales/tests.py
git commit -m "feat: Sales Order detail now shows total invoiced amount across all related invoices, not just the latest"
```

---

## Task 8: General Ledger report has no filters at all (New Correction #2)

**What was actually found:** `billing/_gap14_31_views.py:202-215` (`general_ledger`) has zero query-parameter handling — it iterates `JournalEntryLine.objects.select_related('entry').order_by(...)` unconditionally, dumping every ledger line ever posted with no date range and no account filter. This is a direct, literal match for the client's request.

**Files:**
- Modify: `billing/_gap14_31_views.py:202-215`
- Modify: `templates/billing/general_ledger.html`
- Test: `billing/tests.py`

- [ ] **Step 1: Write the failing test**

Add to `billing/tests.py`:

```python
class GeneralLedgerFilterTests(_TestCase):

    def setUp(self):
        self.user = _User.objects.create_superuser(username='gl_filter_admin', email='glfilter@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)
        from billing.models import JournalEntry, JournalEntryLine
        old = JournalEntry.objects.create(entry_date='2020-01-01', description='Old entry', reference='OLD-1')
        JournalEntryLine.objects.create(entry=old, account='Cash', debit=_Decimal('100'))
        JournalEntryLine.objects.create(entry=old, account='Sales', credit=_Decimal('100'))
        recent = JournalEntry.objects.create(entry_date='2026-08-01', description='Recent entry', reference='RECENT-1')
        JournalEntryLine.objects.create(entry=recent, account='Bank', debit=_Decimal('200'))
        JournalEntryLine.objects.create(entry=recent, account='Sales', credit=_Decimal('200'))

    def test_date_range_filter_excludes_entries_outside_range(self):
        response = self.client.get(_reverse('billing:general_ledger'), {'from_date': '2026-01-01', 'to_date': '2026-12-31'})
        self.assertEqual(response.status_code, 200)
        account_names = {a['name'] for a in response.context['accounts']}
        self.assertIn('Bank', account_names)
        self.assertNotIn('Cash', account_names)

    def test_account_filter_shows_only_the_selected_account(self):
        response = self.client.get(_reverse('billing:general_ledger'), {'account': 'Sales'})
        self.assertEqual(response.status_code, 200)
        account_names = {a['name'] for a in response.context['accounts']}
        self.assertEqual(account_names, {'Sales'})
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python manage.py test billing.tests.GeneralLedgerFilterTests -v 2`
Expected: FAIL — both tests see all accounts regardless of query params (`Cash` still present in the date-range test; both `Bank` and `Sales` present in the account-filter test).

- [ ] **Step 3: Add filtering to the view**

Replace `billing/_gap14_31_views.py:202-215`:

```python
@login_required
@require_module_action('finance', 'view')
def general_ledger(request):
    lines = JournalEntryLine.objects.select_related('entry').order_by('account', 'entry__entry_date')

    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    account_filter = request.GET.get('account', '').strip()

    if from_date:
        lines = lines.filter(entry__entry_date__gte=from_date)
    if to_date:
        lines = lines.filter(entry__entry_date__lte=to_date)
    if account_filter:
        lines = lines.filter(account=account_filter)

    accounts = {}
    for line in lines:
        a = accounts.setdefault(line.account, {
            'name': line.account, 'debit': Decimal('0'),
            'credit': Decimal('0'), 'entries': [],
        })
        a['debit']  += line.debit
        a['credit'] += line.credit
        a['entries'].append(line)
    for a in accounts.values():
        a['balance'] = a['debit'] - a['credit']
    accounts_list = sorted(accounts.values(), key=lambda x: x['name'])

    all_accounts = list(
        JournalEntryLine.objects.order_by('account').values_list('account', flat=True).distinct()
    )

    return render(request, 'billing/general_ledger.html', {
        'accounts': accounts_list,
        'all_accounts': all_accounts,
        'from_date': from_date or '',
        'to_date': to_date or '',
        'selected_account': account_filter,
    })
```

(Add `from accounts.permissions import require_module_action` to the top of `billing/_gap14_31_views.py` if not already imported — check first.)

- [ ] **Step 4: Add the filter form to the template**

In `templates/billing/general_ledger.html`, add above the existing accounts table (read the file first to find the right insertion point):

```html
<form method="get" class="search-bar">
  <input type="date" name="from_date" value="{{ from_date }}" placeholder="From date">
  <input type="date" name="to_date" value="{{ to_date }}" placeholder="To date">
  <select name="account" class="form-select" style="max-width:220px;">
    <option value="">All accounts</option>
    {% for acc in all_accounts %}
      <option value="{{ acc }}" {% if acc == selected_account %}selected{% endif %}>{{ acc }}</option>
    {% endfor %}
  </select>
  <button type="submit" class="btn btn-primary btn-sm">Filter</button>
  <a href="{% url 'billing:general_ledger' %}" class="btn btn-outline-secondary btn-sm">Clear</a>
</form>
```

- [ ] **Step 5: Run it to verify it passes**

Run: `python manage.py test billing.tests.GeneralLedgerFilterTests -v 2`
Expected: PASS.

- [ ] **Step 6: Run the full billing suite**

Run: `python manage.py test billing`
Expected: all pass — the new `@require_module_action('finance', 'view')` decorator also closes part of Task 10 (RBAC), confirm no existing test hits `general_ledger` as a non-finance role expecting 200 (if one does, it was testing the RBAC gap itself and its expectation should flip to 403).

- [ ] **Step 7: Commit**

```bash
git add billing/_gap14_31_views.py templates/billing/general_ledger.html billing/tests.py
git commit -m "feat: add date-range and account filters to the General Ledger report"
```

---

## Task 9: The "403 — Submitted documents cannot be edited" error is a dead end (New Correction #6)

**What was actually found:** the exact string `<h1>403 — Submitted documents cannot be edited. Cancel and amend instead.</h1>` is returned as a raw `HttpResponseForbidden` from **9 separate call sites** (`billing/views.py:135`, `sales/views.py:639,797,991,1014`, `vas/views.py:105,176,247,577`). The guard itself is correct (a Submitted document genuinely shouldn't be directly editable), but the response is a bare, unstyled HTML fragment with no link back anywhere, let alone to the actual Cancel-and-Amend action — it tells the user what to do without giving them any way to do it. This is the literal, repeated symptom behind the client's report.

**Files:**
- Modify: `accounts/views.py` (new shared helper)
- Modify: `billing/views.py`, `sales/views.py`, `vas/views.py` (9 call sites)
- Create: `templates/accounts/submitted_locked.html`
- Test: `sales/tests.py` (one representative call site — the pattern is identical at all 9, not worth 9 near-identical tests)

**Interfaces:**
- Produces: `accounts.views.submitted_document_locked(request, document_type, cancel_amend_url) -> HttpResponse` — renders a real page (403 status) with a working link to the document's own detail page, where the existing Cancel button lives.

- [ ] **Step 1: Write the failing test**

Add to `sales/tests.py` (using the `order_update` call site as the representative case — line 639):

```python
class SubmittedDocumentLockedPageTests(TestCase):

    def test_editing_a_submitted_order_shows_a_working_cancel_amend_link(self):
        from django.test import Client
        from django.urls import reverse
        from accounts.models import User
        from customers.models import Customer
        from sales.models import VehicleSalesOrder

        user = User.objects.create_superuser(username='locked_doc_admin', email='lockeddoc@example.com', password='Test-Pass-123!')
        customer = Customer.objects.create(full_name='Locked Doc Customer', phone='9000000050')
        order = VehicleSalesOrder.objects.create(customer=customer, booking_amount=Decimal('1000'), total_amount=Decimal('50000'))
        order.submit(user)

        client = Client()
        client.force_login(user)
        response = client.get(reverse('sales:order_update', args=[order.pk]))

        self.assertEqual(response.status_code, 403)
        # The old bug: a bare <h1> with no link. The fix: an actual link
        # back to the order detail page, where Cancel & Amend lives.
        self.assertContains(response, reverse('sales:order_detail', args=[order.pk]), status_code=403)
        self.assertContains(response, 'Cancel', status_code=403)
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python manage.py test sales.tests.SubmittedDocumentLockedPageTests -v 2`
Expected: FAIL — the response body is the bare `<h1>` string, doesn't contain the order-detail URL.

- [ ] **Step 3: Create the shared helper and template**

In `accounts/views.py`, add near the top-level view functions (after imports, before the first view):

```python
def submitted_document_locked(request, detail_url):
    """Render a real page (not a bare error string) when a user tries to
    edit a Submitted document directly. Points them at the document's own
    detail page, where the existing Cancel & Amend action actually lives —
    the previous bare HttpResponseForbidden told the user what to do
    without giving them any way to do it."""
    from django.http import HttpResponseForbidden
    from django.template.loader import render_to_string
    html = render_to_string('accounts/submitted_locked.html', {'detail_url': detail_url}, request=request)
    return HttpResponseForbidden(html)
```

Create `templates/accounts/submitted_locked.html`:

```html
{% extends 'base.html' %}

{% block page_title %}Document Locked{% endblock %}

{% block content %}
<div class="card mb-4">
  <div class="card-body" style="padding:28px;text-align:center;">
    <i class="fas fa-lock" style="font-size:32px;color:#DC2626;margin-bottom:12px;"></i>
    <h2 style="font-size:20px;margin-bottom:8px;">This document is submitted and locked</h2>
    <p style="color:#64748B;margin-bottom:20px;">
      Submitted documents can't be edited directly. Cancel it to unlock it for
      correction — cancelling opens an Amend action that creates a fresh,
      linked draft copy carrying the same history.
    </p>
    <a href="{{ detail_url }}" class="btn btn-primary">
      <i class="fas fa-arrow-left me-1"></i> Go to the document — Cancel &amp; Amend from there
    </a>
  </div>
</div>
{% endblock %}
```

- [ ] **Step 4: Replace all 9 call sites**

In each of the 9 locations, replace:

```python
        return HttpResponseForbidden('<h1>403 — Submitted documents cannot be edited. Cancel and amend instead.</h1>')
```

with a call to the shared helper, passing that specific document's own detail URL. For example, `sales/views.py:639` (inside `order_update`, where `order` is already in scope):

```python
        from accounts.views import submitted_document_locked
        return submitted_document_locked(request, reverse('sales:order_detail', args=[order.pk]))
```

Repeat for the other 8 call sites, using each function's own document variable and detail URL name (`sales/views.py:797` → `delivery` → `sales:order_detail` args=[delivery.sales_order_id] since deliveries don't have their own detail page, confirm by reading the surrounding function; `sales/views.py:991,1014` → read the enclosing function to find the right variable/URL; `billing/views.py:135` → `invoice` → `billing:invoice_detail`; `vas/views.py:105,176,247,577` → read each enclosing function for its document variable and matching detail URL name). Add `from django.urls import reverse` at the top of each file if not already imported.

- [ ] **Step 5: Run it to verify it passes**

Run: `python manage.py test sales.tests.SubmittedDocumentLockedPageTests -v 2`
Expected: PASS.

- [ ] **Step 6: Run the full regression suite**

Run: `python manage.py test`
Expected: all pass — this touches 9 call sites across 3 apps, run the whole suite, not just the affected apps.

- [ ] **Step 7: Commit**

```bash
git add accounts/views.py templates/accounts/submitted_locked.html billing/views.py sales/views.py vas/views.py sales/tests.py
git commit -m "fix: submitted-document-locked error now links to the actual Cancel & Amend action instead of dead-ending"
```

---

## Task 10: General Ledger / Journal Entry views are missing the fine-grained Display permission (part of New Correction #11)

**What was actually found:** `RolePermissionMiddleware` (`accounts/middleware.py:24-74`) correctly blocks a role from an entire URL namespace it has no access to (e.g. a Sales Executive can't reach any `billing:` URL). But *within* an allowed namespace, the finer-grained Create/Display/Edit/Delete matrix (`accounts.permissions.user_can_perform`, wired via `@require_module_action`) is inconsistently applied: `general_ledger` and `journal_entry_detail` in `billing/_gap14_31_views.py` have only `@login_required`, with no `@require_module_action` check at all — so a role with "Display" unchecked for Finance in the Module Access matrix can still view the full General Ledger and any Journal Entry detail. Task 8 already added the missing decorator to `general_ledger`; this task adds it to `journal_entry_detail` and audits the rest of billing's list/detail views for the same gap.

**Files:**
- Modify: `billing/_gap14_31_views.py` (`journal_entry_detail`)
- Test: `billing/tests.py`

- [ ] **Step 1: Write the failing test**

Add to `billing/tests.py`:

```python
class JournalEntryDisplayPermissionTests(_TestCase):

    def setUp(self):
        from accounts.models import Role, ModulePermission
        self.role = Role.objects.create(role_name='No Finance Display Role')
        ModulePermission.objects.create(role=self.role, module='finance', can_view=False)
        self.user = _User.objects.create(username='no_finance_display', email='nofinance@example.com', role=self.role)
        self.user.set_password('Test-Pass-123!')
        self.user.save()
        self.client.force_login(self.user)
        from billing.models import JournalEntry
        self.entry = JournalEntry.objects.create(entry_date='2026-08-01', description='Blocked entry test', reference='BLOCK-1')

    def test_journal_entry_detail_blocked_when_display_permission_is_off(self):
        response = self.client.get(_reverse('billing:journal_entry_detail', args=[self.entry.pk]))
        self.assertEqual(response.status_code, 403)
```

(If `Role`/`ModulePermission` field names differ from this guess — e.g. `can_view` might be named differently, or `ModulePermission.module` might use a `MODULE_CHOICES` constant rather than a raw string — read `accounts/models.py`'s `ModulePermission` class first and adjust the test to match the real field/constant names before running it.)

- [ ] **Step 2: Run it to verify it fails**

Run: `python manage.py test billing.tests.JournalEntryDisplayPermissionTests -v 2`
Expected: FAIL — `journal_entry_detail` returns 200, not 403, since it currently has no permission check beyond being logged in.

- [ ] **Step 3: Add the decorator**

In `billing/_gap14_31_views.py`, find `journal_entry_detail` and add the decorator matching the pattern already used on `journal_entry_create` in the same file:

```python
@login_required
@require_module_action('finance', 'view')
def journal_entry_detail(request, pk):
```

- [ ] **Step 4: Run it to verify it passes**

Run: `python manage.py test billing.tests.JournalEntryDisplayPermissionTests -v 2`
Expected: PASS.

- [ ] **Step 5: Audit the rest of billing's read views for the same gap**

Run: `grep -n "^def \|@require_module_action\|@login_required" billing/views.py billing/_gap14_31_views.py` and read the output. For every view with only `@login_required` (no `@require_module_action`), decide deliberately: is it meant to be gated only at the namespace level (e.g. a dashboard everyone in the module should see), or does it expose specific financial data that should respect the Display permission? For each one judged to need it, add `@require_module_action('finance', 'view')` the same way, with its own failing-test-first cycle following Steps 1-4's pattern. Do not blanket-apply without judgment — a view like `invoice_search` might be intentionally open to anyone with `billing` namespace access, and a mismatch there would be a new, self-inflicted bug, not a fix.

- [ ] **Step 6: Run the full billing suite**

Run: `python manage.py test billing`
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add billing/_gap14_31_views.py billing/tests.py
git commit -m "fix: enforce the Display permission on Journal Entry detail (and any other confirmed gaps found in the billing view audit)"
```

---

## Task 11: Re-verify the Supplier form against the live reference server (Pending Correction #2)

**What was actually found:** the Supplier *model*, *form*, and *template* (`masters/models.py:20-56`, `masters/forms.py:18-39`, `templates/masters/supplier_form.html`) already correctly include the 5 fields a previous round added (Country, Supplier Type, Is Transporter, Is Prepaid Supplier, Supplier Limit Amount) — confirmed by reading all three files directly. But `reference_erp_spec/26_Master.md`'s own Supplier section says **"NOT FOUND on server (fetch failed or renamed) — needs manual re-check"** — the original bulk extraction never actually captured this doctype's real field list. So there's no way to confirm from the existing spec whether the 5 already-added fields are the *complete* set the reference server actually has, or whether the client is still seeing gaps because more fields exist there that were never pulled. This needs a live check, not more guessing from screenshots.

**Files:**
- Create: `reference_erp_spec/tools/check_supplier_fields.py`
- Modify: `masters/models.py`, `masters/forms.py`, `templates/masters/supplier_form.html` (only if the live check finds a real gap)
- Test: `masters/tests.py` (only if a model change results)

- [ ] **Step 1: Write the live-check script**

Create `reference_erp_spec/tools/check_supplier_fields.py` (same `.env`-based credential loading pattern as `refresh_check.py` — never hardcode credentials):

```python
"""
reference_erp_spec/tools/check_supplier_fields.py

One-shot re-check of the reference server's Supplier doctype field list.
The original bulk extraction failed for this specific doctype (recorded
in reference_erp_spec/26_Master.md as "NOT FOUND on server"); this pulls
it directly so the client's "important fields are missing" report can be
checked against real data instead of guessed from screenshots.

Run: python reference_erp_spec/tools/check_supplier_fields.py
"""
import json
import os
import sys

import requests


def load_env(path='.env'):
    values = {}
    if not os.path.exists(path):
        return values
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, _, value = line.partition('=')
            values[key.strip()] = value.strip()
    return values


def main():
    env = {**load_env(), **os.environ}
    base_url = env.get('REFERENCE_ERP_URL')
    user = env.get('REFERENCE_ERP_USER')
    password = env.get('REFERENCE_ERP_PASSWORD')
    if not (base_url and user and password):
        print('Missing REFERENCE_ERP_URL / REFERENCE_ERP_USER / REFERENCE_ERP_PASSWORD in .env')
        sys.exit(1)

    site_root = base_url.split('/app/')[0]
    session = requests.Session()
    login = session.post(f'{site_root}/api/method/login', data={'usr': user, 'pwd': password}, timeout=30)
    login.raise_for_status()

    resp = session.get(f'{site_root}/api/resource/DocType/Supplier', timeout=60)
    resp.raise_for_status()
    data = resp.json().get('data', {})
    fields = data.get('fields', [])

    print(f'Supplier doctype: {len(fields)} fields')
    for f in fields:
        print(f"  {f.get('fieldname')} | {f.get('fieldtype')} | {f.get('label')} | reqd={f.get('reqd')}")

    out_path = os.path.join(os.path.dirname(__file__), '..', '_raw_api_data', 'std_doctypes_full', 'Supplier.json')
    with open(out_path, 'w', encoding='utf-8') as out:
        json.dump({'data': data}, out, indent=2)
    print(f'Wrote full field data to {out_path}')


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: Run it**

Add `REFERENCE_ERP_URL`/`REFERENCE_ERP_USER`/`REFERENCE_ERP_PASSWORD` to the local, gitignored `.env` (same as the earlier audit's Task 1 — never commit these). Run: `python reference_erp_spec/tools/check_supplier_fields.py`
Expected: prints the real field list and overwrites the stub `Supplier.json` with real data (previously just `{"message": ...}` per the earlier audit session's finding).

- [ ] **Step 3: Compare against the Django model**

Diff the printed reference field list against `masters/models.py`'s `Supplier` class (lines 20-56). For every reference field with no Django equivalent, note it. Common ERPNext Supplier fields worth specifically checking for since they weren't in the original 5-field fix: `default_currency`, `payment_terms`, `credit_days`, `bank_account_details`, `tax_id`/`pan`.

- [ ] **Step 4: If a real gap is found, close it with TDD**

For each missing field: write a failing test asserting the field exists on the model and appears in the form (following the exact pattern used for `is_transporter`/`is_prepaid_supplier` in the existing `masters/tests.py`, if such a test exists — check first), add the model field, `makemigrations`, add to the form (it'll be auto-included via `SupplierForm`'s `exclude`-based `Meta`, per Task 11's own investigation — no form change needed unless a new field needs special widget treatment), add to the template following the existing field-block pattern in `templates/masters/supplier_form.html`, run the test, commit.

If the live check finds **no** gap (the 5 already-added fields really are the complete set), skip straight to Step 5 — this task's value was confirming that, not inventing work.

- [ ] **Step 5: Commit the check script and findings regardless of outcome**

```bash
git add reference_erp_spec/tools/check_supplier_fields.py reference_erp_spec/_raw_api_data/std_doctypes_full/Supplier.json
git commit -m "audit: live re-check of reference Supplier doctype fields (was NOT FOUND in original extraction)"
```

(If Step 4 made model/form/template changes, that's a separate commit per the TDD steps above, following the same message style as other fix commits in this plan.)

---

## Task 12: Purchase Estimation module (New Correction #7)

**What was actually found:** `spares/models.py` has `SparesPurchaseEstimationMaster`/`SparesPurchaseEstimationItem`/`SparesPurchaseEstimationLabor` models with full CRUD views, and it's a real sidebar entry. The client explicitly says "Purchase Estimation is not required" — this reads as a scope decision (remove from view), not a bug report. Hiding it from the default sidebar nav is safe, fast, and fully reversible (the Module Access feature — `accounts/views.py:629,641` — already supports hiding any module per-role, but per its own docstring "Superusers always see everything, regardless of overrides," which won't hide it for an admin tester; this task hides it from the *default* nav template directly, which does affect superusers too).

**Files:**
- Modify: `templates/base.html` (find the "Purchase Estimation" sidebar `<a>` link — search for it first, don't guess the line number)
- Test: none required (a template-only visibility change; covered by the existing e2e suite not breaking)

- [ ] **Step 1: Find the exact sidebar entry**

Run: `grep -n -i "purchase estimation" templates/base.html`

- [ ] **Step 2: Remove or comment out the sidebar link**

Remove the matched `<a class="sidebar-link" ...>Purchase Estimation</a>` line (and its enclosing `<li>`/wrapper if the surrounding markup requires one — read 5 lines of context around the match first). Leave the underlying URLs/views/models untouched — this is a nav-visibility change, not a data-deletion decision, and the client may want the data preserved even if the module is hidden from daily use.

- [ ] **Step 3: Run the full e2e suite**

Run: `python manage.py test e2e`
Expected: all pass — confirms removing the sidebar link didn't break any test that clicks through the sidebar.

- [ ] **Step 4: Commit**

```bash
git add templates/base.html
git commit -m "chore: hide Purchase Estimation from the sidebar per client request — not required, data/views untouched"
```

---

## Task 13: Sidebar simplification (New Correction #8) — decision needed, not a unilateral code change

**What was actually found:** "too many unnecessary modules in the sidebar" has no single, specific target the way Task 12's item does — acting on it without knowing exactly which modules the client considers unnecessary risks hiding something they actually need, which would just generate a new corrections report. This is a scope/product conversation, not a bug.

**What this task actually does:** produce a concrete, client-reviewable candidate list (not a code change) by cross-referencing our full sidebar link list against the reference server's own navigation structure, which is already fully captured in `reference_erp_spec/`.

- [ ] **Step 1: Extract every sidebar link's label and target from our app**

```bash
grep -oP '(?<=sidebar-link[^>]{0,200}>)[^<]+' templates/base.html
```

(If `grep -P` isn't available in the shell being used, use `python -c "import re; print(re.findall(r'sidebar-link[^>]*>([^<]+)', open('templates/base.html', encoding=\"utf-8\").read()))"` instead — confirmed working around a known `grep -P` locale issue on this machine.)

- [ ] **Step 2: Extract the reference server's actual main-nav module list**

Read `reference_erp_spec/README.md`'s module-group list (files `00_*.md` through `26_*.md`, 27 groups) — these ARE the reference server's real navigation structure, already reverse-engineered. Cross-reference: any of our sidebar entries with **no corresponding concept** in that list, or that map only to something explicitly documented in `reference_erp_spec/27_not_in_main_nav.md` (141 doctypes confirmed NOT in the reference's main nav), is a legitimate candidate for hiding or demoting.

- [ ] **Step 3: Write the candidate list as a short client-facing note**

Create `docs/audit/SIDEBAR_SIMPLIFICATION_CANDIDATES.md` with a table: `Our sidebar label | Reference equivalent (or "none found") | Recommendation (hide / keep / merge)`. Do not act on any row automatically — this file is the artifact for the next client conversation, matching how `docs/audit/DEVIATIONS.md` already works for the rest of this project (evidence-backed, human-decided, not silently auto-applied).

- [ ] **Step 4: Commit**

```bash
git add docs/audit/SIDEBAR_SIMPLIFICATION_CANDIDATES.md
git commit -m "docs: sidebar-simplification candidate list for client review (New Correction #8)"
```

---

## Self-Review Notes

- **Spec coverage:** all 3 Pending Corrections (search, Supplier fields, tax calc) and all 11 New Corrections are covered: #1→Task 4, #2→Task 8, #3→Task 6, #4→Task 5, #5→Task 7, #6→Task 9, #7→Task 12, #8→Task 13, #9/#10→covered by the already-in-progress Tiers 3-8 audit (explicitly noted in Global Constraints, not silently dropped), #11→Task 10 (+ the `general_ledger` half already gated in Task 8).
- **Placeholder scan:** Tasks 2, 10, and 11 each have one step that says "read the file first, don't guess the line number / field name" rather than a fabricated exact reference — this is deliberate, not a placeholder: the alternative was inventing a plausible-sounding class/field name that might not match the real code, which is worse than an explicit "confirm this first" instruction. Every other step has real, complete code.
- **Type/name consistency:** `recompute_total_from_items(parent, related_name, amount_field)` (Task 3) is called identically by `VehicleSalesOrder.recompute_totals` (Task 4), `Invoice.recompute_totals` (Task 5), and `VehicleDelivery.recompute_totals` (Task 6) — same signature, same import path, verified across all three call sites in this plan text.

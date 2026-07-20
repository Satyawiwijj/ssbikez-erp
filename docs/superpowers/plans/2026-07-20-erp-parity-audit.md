# ERP Reference-Server Parity Audit & Delivery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce an evidence-backed, row-by-row comparison between the client's live reference ERP test server and this Django app, fix every confirmed real deviation with a regression test, and ship tonight with a sign-off document the client can independently verify — replacing ten rounds of narrative "we checked it and it's fine" reports (which the client has kept rejecting) with a checklist they can audit themselves.

**Architecture:** Two new lightweight tools extract/scaffold the comparison ledger (`docs/audit/PARITY_MATRIX.csv`), a manual-but-structured walkthrough fills it module-by-module in priority order (reusing the reference spec already captured in `reference_erp_spec/`), confirmed gaps get triaged into `docs/audit/DEVIATIONS.md`, each real bug goes through a TDD fix cycle against the existing Django test suite (138 tests) and Playwright e2e suite, and the whole thing closes with a full regression run plus `docs/audit/PARITY_SIGNOFF.md`.

**Tech Stack:** Django 6.0.7 / Python 3.12 (this app), Frappe/ERPNext (reference server, custom `ssbikez` app), `requests` for scripted API reads against the reference server, `python manage.py test` / `python manage.py test e2e` (Playwright) for verification.

## Global Constraints

- Reference server: `http://95.216.169.103/app/ssbikez` — Frappe/ERPNext, custom `ssbikez` app, `Ssbikez` module. Prior extraction recorded a baseline of **429 custom doctypes** and **201 client scripts** (`reference_erp_spec/README.md`) across 27 navigation groups (`reference_erp_spec/00_*.md` through `26_*.md`), plus 92 standard-doctype schemas (`30_standard_doctypes_full_schema.md`) and one fully live-verified flow chain (`31_LIVE_VERIFIED_flows.md`, Sales chain only).
- Reference server credentials (`administrator` / `<redacted -- see local .env>`) are for this test instance only, supplied directly by the user for this audit. They go in a local, gitignored `.env` — **never hardcoded in a script, never committed, never typed into a browser login form by an agent.** All scripted reads use `requests` against Frappe's `/api/method/login` + `/api/resource/...`, matching the exact method the existing `reference_erp_spec/` extraction already used (confirmed by its own `README.md`: "Extracted directly from the live test server's Frappe/ERPNext REST API").
- Our app's document lifecycle is `Draft → Submitted → Cancelled → Amended` (`accounts.models.DocStatusMixin`), deliberately mirroring the reference ERP's `docstatus` — this is the contract every module comparison checks against.
- Existing regression floor, must stay green throughout: `python manage.py test` (138 tests), `python manage.py test e2e` (Playwright, 5 flow files), and the ad hoc scripts `check_all.py` / `run_full_test.py` for a fast full-route smoke pass.
- No silent scope-dropping: 429 doctypes cannot be re-verified byte-for-byte in one evening. Any module/doctype not walked through tonight goes into `docs/audit/PARITY_SIGNOFF.md` under "Not covered this pass" with a reason — never just omitted.
- Priority order for the walkthrough (highest business/financial impact first, matching the reference spec's own module grouping): **(1) New Vehicle Sales chain — Enquiry→Appointment→Order→Delivery→Invoice/GST, (2) Billing/Payments/GL, (3) Service/Job Card pipeline, (4) Spares (Purchase/Counter Sale/Stock), (5) RTO/Exchange, (6) Used Vehicles, (7) VAS (AMC/RSA/Protection Plus), (8) Masters/Admin/Role permissions.** Tiers 1–2 are LIVE_VERIFIED-grade already in the spec and get re-confirmed fastest; tiers 3–8 need fresh live comparison.
- Every fix follows TDD: failing test first (Django `TestCase` for model/view logic, `e2e/` Playwright for anything a browser-only bug could hide), then the minimal fix, then green, then commit.

---

## File Structure

| File | Purpose |
|---|---|
| `reference_erp_spec/tools/refresh_check.py` (new) | Logs into the live reference server via the Frappe REST API and confirms the recorded baseline (429 doctypes / 201 client scripts) is still current before trusting the existing spec docs. |
| `reference_erp_spec/tools/build_matrix_skeleton.py` (new) | Parses the already-extracted `_raw_api_data/*.json` into the starting rows of the parity matrix (reference-side columns only). |
| `docs/audit/PARITY_MATRIX.csv` (new) | The master row-per-field ledger: reference doctype/field/rule vs. our Django model/field/view vs. Match/Deviation/Missing/Descoped vs. evidence. This is the artifact the client can check row by row. |
| `docs/audit/DEVIATIONS.md` (new) | Triaged queue of every confirmed real gap pulled from the matrix, ranked by business impact, each with a status (Fixed / In Progress / Descoped). |
| `docs/audit/PARITY_SIGNOFF.md` (new) | Final delivery note: what was audited, what matched, what was fixed (with commit refs), what's a deliberate scope difference, what's explicitly not covered tonight. |
| `billing/models.py` (modify) | Worked fix-cycle example: `Invoice.cancel()` currently doesn't reverse its auto-posted GL entry (documented accepted risk in `CLIENT_GUIDE.md` §9) — closed as part of this pass since "no deviation" includes internal accounting correctness, not just reference-server parity. |
| `billing/tests.py` (modify) | Test for the GL-reversal fix above. |

---

## Task 1: Freshness probe against the live reference server

**Files:**
- Create: `reference_erp_spec/tools/refresh_check.py`
- Create: `docs/audit/FRESHNESS_CHECK.md`

**Interfaces:**
- Produces: confirmation (or contradiction) of the baseline counts (`429` custom doctypes, `201` client scripts) that every later task treats as ground truth. If this task finds drift, later tasks must re-pull the affected module's spec file before comparing against it — flag this explicitly in `docs/audit/FRESHNESS_CHECK.md`.

- [ ] **Step 1: Add reference-server credentials to the local, gitignored `.env`**

Add these two lines to `.env` (already gitignored — confirm with `git check-ignore .env` returns the path):

```
REFERENCE_ERP_URL=http://95.216.169.103/app/ssbikez
REFERENCE_ERP_USER=administrator
REFERENCE_ERP_PASSWORD=<redacted -- see local .env>
```

- [ ] **Step 2: Write the freshness-check script**

```python
"""
reference_erp_spec/tools/refresh_check.py

One-shot check: log into the live reference server via Frappe's REST API
and compare its current doctype/client-script counts against the baseline
recorded in reference_erp_spec/README.md (429 custom doctypes, 201 client
scripts). If they match, the existing spec docs are trustworthy as-is for
tonight's comparison. If they don't, print exactly which counts moved so
the affected module file(s) can be re-pulled before use.

Run: python reference_erp_spec/tools/refresh_check.py
"""
import os
import sys

import requests

BASELINE_DOCTYPE_COUNT = 429
BASELINE_CLIENT_SCRIPT_COUNT = 201


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
    login = session.post(
        f'{site_root}/api/method/login',
        data={'usr': user, 'pwd': password},
        timeout=30,
    )
    login.raise_for_status()

    doctype_resp = session.get(
        f'{site_root}/api/resource/DocType',
        params={'filters': '[["module","=","Ssbikez"],["custom","=",1]]', 'limit_page_length': 0},
        timeout=60,
    )
    doctype_resp.raise_for_status()
    live_doctype_count = len(doctype_resp.json().get('data', []))

    script_resp = session.get(
        f'{site_root}/api/resource/Client Script',
        params={'limit_page_length': 0},
        timeout=60,
    )
    script_resp.raise_for_status()
    live_script_count = len(script_resp.json().get('data', []))

    print(f'Live custom doctype count (Ssbikez module): {live_doctype_count} (baseline: {BASELINE_DOCTYPE_COUNT})')
    print(f'Live client script count: {live_script_count} (baseline: {BASELINE_CLIENT_SCRIPT_COUNT})')

    drifted = (live_doctype_count != BASELINE_DOCTYPE_COUNT) or (live_script_count != BASELINE_CLIENT_SCRIPT_COUNT)
    print('DRIFT DETECTED — re-pull affected spec files before trusting them.' if drifted else 'Baseline confirmed current.')
    sys.exit(1 if drifted else 0)


if __name__ == '__main__':
    main()
```

- [ ] **Step 3: Run it**

Run: `python reference_erp_spec/tools/refresh_check.py`
Expected: prints both live counts and either "Baseline confirmed current." (exit 0) or "DRIFT DETECTED" (exit 1) naming which count moved.

- [ ] **Step 4: Record the result**

Write `docs/audit/FRESHNESS_CHECK.md` with the script's output verbatim, a timestamp, and — if drift was found — which specific `reference_erp_spec/NN_*.md` files are now suspect and must be re-pulled before Task 3 relies on them for that module.

- [ ] **Step 5: Commit**

```bash
git add reference_erp_spec/tools/refresh_check.py docs/audit/FRESHNESS_CHECK.md
git commit -m "audit: add reference-server freshness probe"
```

---

## Task 2: Build the parity matrix skeleton

**Files:**
- Create: `reference_erp_spec/tools/build_matrix_skeleton.py`
- Create: `docs/audit/PARITY_MATRIX.csv`

**Interfaces:**
- Consumes: `reference_erp_spec/_raw_api_data/doctypes_raw/*.json` — one file per custom doctype (429 files, confirmed present and matching the Task-1-confirmed baseline count), each shaped `{"data": {"name", "module", "istable", "issingle", "fields": [{"fieldname", "fieldtype", "reqd", "label", ...}, ...]}}`. (Verified directly against the actual extracted files while preparing this plan — `custom_doctypes.json`/`custom_fields.json` were the wrong source: `custom_fields.json` is the 630 bolt-on "Custom Field" records used for standard-doctype customizations per `28_standard_doctype_customizations.md`, not the native field lists of the 429 custom doctypes; those native fields live per-file in `doctypes_raw/`.)
- Produces: `docs/audit/PARITY_MATRIX.csv` with columns `module,doctype,field,fieldtype,mandatory,reference_note,django_app,django_model,django_field,status,evidence` — the last five columns start blank and are filled by Task 3/7's walkthrough. `status` is one of `Match / Deviation / Missing / Descoped-tonight / Deliberate-difference`.

- [ ] **Step 1: Write the skeleton builder**

```python
"""
reference_erp_spec/tools/build_matrix_skeleton.py

Turns the already-extracted reference-server field data into the starting
rows of docs/audit/PARITY_MATRIX.csv. Reference-side columns are filled
from the per-doctype raw API dumps in doctypes_raw/; the Django-side and
status columns are left blank for the manual walkthrough (Task 3/7 of the
audit plan) to fill in.

Run: python reference_erp_spec/tools/build_matrix_skeleton.py
"""
import csv
import glob
import json
import os

RAW_DOCTYPES_DIR = os.path.join(os.path.dirname(__file__), '..', '_raw_api_data', 'doctypes_raw')
OUT_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'docs', 'audit', 'PARITY_MATRIX.csv')

COLUMNS = [
    'module', 'doctype', 'field', 'fieldtype', 'mandatory', 'reference_note',
    'django_app', 'django_model', 'django_field', 'status', 'evidence',
]


def main():
    rows = []
    doctype_files = sorted(glob.glob(os.path.join(RAW_DOCTYPES_DIR, '*.json')))
    for path in doctype_files:
        with open(path, encoding='utf-8') as f:
            raw = json.load(f)
        dt = raw.get('data', raw)
        name = dt.get('name', os.path.splitext(os.path.basename(path))[0])
        module = dt.get('module', 'Ssbikez')
        fields = dt.get('fields', [])
        if not fields:
            rows.append([module, name, '', '', '', 'no fields recorded (istable/issingle config doctype?)', '', '', '', '', ''])
            continue
        for field in fields:
            rows.append([
                module, name,
                field.get('fieldname', ''), field.get('fieldtype', ''),
                'yes' if field.get('reqd') else 'no',
                (field.get('label') or '').strip(),
                '', '', '', '', '',
            ])

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(COLUMNS)
        writer.writerows(rows)

    print(f'Wrote {len(rows)} rows from {len(doctype_files)} doctype files to {OUT_PATH}')


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: Run it and sanity-check row count**

Run: `python reference_erp_spec/tools/build_matrix_skeleton.py`
Expected: `Wrote <N> rows from 429 doctype files to .../docs/audit/PARITY_MATRIX.csv` where N is in the low thousands. Open the file and confirm the header row matches the 11 columns above and that `New Vehicle Sale Item Child` and `Vehicle Number Child` appear (confirmed present in `doctypes_raw/`, and already deep-dived in `31_LIVE_VERIFIED_flows.md`). Note: `Purchase Invoice` and `Journal Entry` are *standard* Frappe/ERPNext doctypes (only customized, not custom-created), so they intentionally do NOT appear in this skeleton — their field data lives separately in `reference_erp_spec/_raw_api_data/std_doctypes_full/` and `30_standard_doctypes_full_schema.md`, and Task 3/7 cross-reference those files directly rather than via this CSV.

- [ ] **Step 3: Commit**

```bash
git add reference_erp_spec/tools/build_matrix_skeleton.py docs/audit/PARITY_MATRIX.csv
git commit -m "audit: scaffold the parity matrix from extracted reference-server data"
```

---

## Task 3: Walk Tier 1 (New Vehicle Sales chain) — worked example for the repeatable procedure

This is the template every later tier (Task 7) repeats. Tier 1 goes first because it is already **LIVE_VERIFIED** (`reference_erp_spec/31_LIVE_VERIFIED_flows.md`) — real, confirmed reference-server behavior, not inferred from schema alone — so it is the fastest tier to cross-check and it fixes the procedure before spending time on tiers that need fresh live verification.

**Files:**
- Modify: `docs/audit/PARITY_MATRIX.csv` (fill `django_*`/`status`/`evidence` columns for Tier 1 rows)
- Read (no edits): `sales/models.py`, `sales/views.py`, `sales/forms.py`, `customers/models.py`

**Procedure (repeat per doctype/flow-rule):**
1. Pick the next reference fact from the spec (a field row in the matrix, or a numbered behavior in `31_LIVE_VERIFIED_flows.md`).
2. Grep the Django app for the equivalent model/field/view logic.
3. Decide: **Match** (same field, same rule, verified in code) / **Deviation** (field or rule differs) / **Missing** (reference has it, we don't) / **Deliberate-difference** (already explained in `PRODUCTION_DELIVERY_REPORT.md`, e.g. `Customer Vehicle`) / **Descoped-tonight** (not reachable in the time available — must still get a row, not silence).
4. Fill the matrix row(s) with the Django-side facts and a one-line evidence pointer (`file:line` or test name).

- [ ] **Step 1: Cross-check the five confirmed Section-3 behaviors from `31_LIVE_VERIFIED_flows.md` against `sales/`**

For each of the five order-dependent behaviors documented as live-confirmed reference facts, read the corresponding Django logic and record the row:

| Reference fact (from `31_LIVE_VERIFIED_flows.md` §3) | Where to check in this app |
|---|---|
| Setting `customer` on a Sales Order wipes and re-derives `gst_category`/phone from the Customer record | `sales/views.py` — the Sales Order create/edit view's handling of `customer` selection, and whether GST category is derived server-side (not just client JS) |
| `sales_enquiry_form`/link-to-enquiry is *dynamically* mandatory per `Branch.allow_without_enquiry_form` | `sales/models.py` `VehicleSalesOrder`/`SalesEnquiry` — does a `Branch` model field exist and gate the requirement, or is it a static `required=True/False`? |
| Vehicle color/sub-group are derived from the selected price-list record, not entered directly | `sales/forms.py` — the vehicle-selection field(s) on the Sales Order form |
| `total` does not auto-derive from vehicle selection — it comes from a separate priced line-items table | `sales/models.py` — confirm `VehicleSalesOrder` has a distinct line-items child relation separate from vehicle selection, matching the reference's two-step structure |
| GST split (CGST/SGST vs IGST) depends on customer state vs company state | `billing/models.py::split_gst` (already confirmed present — this one should score **Match**, verified in this session while gathering plan context) |

For each row, write the finding directly into `docs/audit/PARITY_MATRIX.csv` (find the row by `doctype`/`field`, fill `django_app=sales` or `billing`, `django_model`, `django_field`, `status`, `evidence=<file>:<line>`).

- [ ] **Step 2: Record the two confirmed reference-app bugs as explicit non-goals**

`31_LIVE_VERIFIED_flows.md` §1 and §3 document two **confirmed bugs in the reference app itself** (orphaned `Vehicle Chasis Number Master` records on failed submit; the `loadDefaultHelmet`/`vehicle_charges_list` race condition). `docs/audit/DEVIATIONS.md` doesn't exist yet (Task 4 is the one that normally triages the matrix into it) — Task 3 creates it now with just this one section, since these two facts are established here, not derivable from the matrix CSV. Create `docs/audit/DEVIATIONS.md`:

```markdown
# Deviations Queue — 2026-07-20 Parity Audit

(Sections below are filled in by Task 4; this file is created early by Task 3
because the "reference-app bugs" section below is established during the
Tier 1 walkthrough, not derived from the parity matrix.)

## Reference-app bugs, deliberately not reproduced

- [x] Orphaned Vehicle Chasis Number Master records on failed Purchase Invoice submit — Deliberate-difference: reference app bug, not reproduced by design — replicating it would itself be a deviation from correct behavior. See `reference_erp_spec/31_LIVE_VERIFIED_flows.md` §1.
- [x] loadDefaultHelmet/vehicle_charges_list race condition on Purchase Invoice submit — Deliberate-difference: reference app bug, not reproduced by design. See `reference_erp_spec/31_LIVE_VERIFIED_flows.md` §1.
```

This prevents an intern QA round from re-flagging "our app doesn't have this bug" as a mismatch.

- [ ] **Step 3: Commit the filled Tier 1 rows**

```bash
git add docs/audit/PARITY_MATRIX.csv
git commit -m "audit: complete Tier 1 (New Vehicle Sales) parity walkthrough"
```

---

## Task 4: Triage confirmed deviations into a ranked queue

**Files:**
- Modify: `docs/audit/DEVIATIONS.md` (created in Task 3 with just the "Reference-app bugs" section — this task adds the rest, it does not overwrite that section)
- Consumes: every `docs/audit/PARITY_MATRIX.csv` row currently marked `Deviation` or `Missing`

- [ ] **Step 1: Extract every non-Match row into the queue**

```python
"""One-off: run interactively or as a script, not committed as a tool
(this is a filter over the matrix, not reusable tooling)."""
import csv

with open('docs/audit/PARITY_MATRIX.csv', encoding='utf-8') as f:
    rows = [r for r in csv.DictReader(f) if r['status'] in ('Deviation', 'Missing')]

for r in rows:
    print(f"- [ ] **{r['doctype']}.{r['field']}** — {r['status']}: {r['reference_note']} (evidence: {r['evidence']})")
```

Run this (e.g. `python -c "..."` or a scratch `.py` file, not committed) after every walkthrough task (3, 7) to regenerate the queue.

- [ ] **Step 2: Extend `docs/audit/DEVIATIONS.md`**

The file already exists (created in Task 3) with a "Reference-app bugs, deliberately not reproduced" section — leave that section exactly as-is and insert the sections below it (or above, your call, but do not delete or edit the existing section's content). Structure as a ranked checklist, highest business/financial impact first (money and stock-integrity bugs before workflow-blocker bugs before cosmetic ones — same ranking rule the existing `PRODUCTION_DELIVERY_REPORT.md` §10 already used successfully):

```markdown
# Deviations Queue — 2026-07-20 Parity Audit

Ranked by business impact. Each item: status is one of Open / Fixed / Descoped.

## Financial / data-integrity

- [ ] <deviation> — Open

## Workflow blockers

- [ ] <deviation> — Open

## Cosmetic / low-impact

- [ ] <deviation> — Open

## Reference-app bugs, deliberately not reproduced

(already populated by Task 3 — keep as-is)

## Not covered this pass

- [ ] <module/doctype> — Descoped-tonight: <reason, e.g. "141 not-in-main-nav doctypes, lower priority than client's active test flows">
```

- [ ] **Step 3: Commit**

```bash
git add docs/audit/DEVIATIONS.md
git commit -m "audit: triage parity-matrix deviations into a ranked fix queue"
```

---

## Task 5: Fix cycle — worked example (GL entry doesn't reverse on Invoice cancel)

This is the repeatable pattern for every `Open` item in `docs/audit/DEVIATIONS.md`. This particular gap is already confirmed real (not hypothetical): `CLIENT_GUIDE.md` §9 documents it as an accepted risk, and reading `billing/models.py` in preparation for this plan confirms `Invoice.submit()` auto-posts a `JournalEntry` (`post_journal_entry`) but `Invoice.cancel()` (inherited from `accounts.models.DocStatusMixin.cancel`) only flips `docstatus` — it never reverses the posted entry. A cancelled invoice permanently leaves its Accounts Receivable/Sales Revenue entries live in the General Ledger, which is a real accounting-correctness deviation, independent of reference-server parity.

**Files:**
- Modify: `billing/models.py:104-137` (the `Invoice` class)
- Test: `billing/tests.py`

**Interfaces:**
- Consumes: `JournalEntry`, `JournalEntryLine` (`billing/models.py:412-478`), `DocStatusMixin.cancel` (`accounts/models.py:60-66`)
- Produces: `Invoice.cancel(user)` now posts a reversing `JournalEntry` (swapped debit/credit) when a GL entry exists, idempotently.

- [ ] **Step 1: Write the failing test**

Add to `billing/tests.py`, in the same style as the existing `InvoiceLifecycleCRUDTests`/`JournalEntryCreateTests` (uses the file's own `_make_order`/`_User`/`_Decimal`/`_TestCase` aliases already defined near line 44-58):

```python
class InvoiceCancelReversesJournalEntryTests(_TestCase):

    def setUp(self):
        self.user = _User.objects.create_superuser(
            username='cancel_admin', email='canceladmin@example.com', password='Test-Pass-123!'
        )
        from billing.models import Invoice
        order = _make_order('CANCELJE1')
        self.invoice = Invoice.objects.create(
            sales_order=order, invoice_number='CANCEL-INV-0001',
            subtotal=_Decimal('50000'), final_amount=_Decimal('50000'),
            invoice_date='2026-08-01',
        )

    def test_cancel_posts_a_reversing_journal_entry(self):
        self.invoice.submit(self.user)
        original_entry = self.invoice.journal_entry
        self.assertEqual(original_entry.total_debit, _Decimal('50000.00'))

        self.invoice.cancel(self.user)

        from billing.models import JournalEntry
        reversal = JournalEntry.objects.filter(
            reference_doctype='billing.Invoice',
            reference_docname=str(self.invoice.pk),
        ).exclude(pk=original_entry.pk).first()
        self.assertIsNotNone(reversal, 'Expected a reversing JournalEntry after cancel')
        self.assertEqual(reversal.lines.get(account='Accounts Receivable').credit, _Decimal('50000.00'))
        self.assertEqual(reversal.lines.get(account='Sales Revenue').debit, _Decimal('50000.00'))

    def test_cancel_twice_does_not_double_reverse(self):
        self.invoice.submit(self.user)
        self.invoice.cancel(self.user)
        from billing.models import JournalEntry
        count_after_first_cancel = JournalEntry.objects.filter(
            reference_doctype='billing.Invoice', reference_docname=str(self.invoice.pk),
        ).count()
        with self.assertRaises(ValueError):
            self.invoice.cancel(self.user)  # DocStatusMixin.cancel already guards non-Submitted state
        count_after_second_attempt = JournalEntry.objects.filter(
            reference_doctype='billing.Invoice', reference_docname=str(self.invoice.pk),
        ).count()
        self.assertEqual(count_after_first_cancel, count_after_second_attempt)
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `python manage.py test billing.tests.InvoiceCancelReversesJournalEntryTests -v 2`
Expected: `test_cancel_posts_a_reversing_journal_entry` FAILS with `AssertionError: None is not None : Expected a reversing JournalEntry after cancel` (no reversal is posted today). `test_cancel_twice_does_not_double_reverse` passes already (cancel-twice is already guarded by `DocStatusMixin`), confirming the test file itself is wired correctly before the fix changes behavior.

- [ ] **Step 3: Implement the fix**

In `billing/models.py`, replace the `Invoice` class's `submit`/`post_journal_entry` block (currently lines 104-137) with:

```python
    def submit(self, user):
        """Draft -> Submitted, then auto-post the sales-recognition entry to
        the General Ledger. GL posting only happens on a *real* submit
        (never for Draft/Cancelled invoices) because DocStatusMixin.submit()
        itself raises ValueError unless docstatus is currently Draft."""
        super().submit(user)
        self.post_journal_entry(user)

    def cancel(self, user):
        """Submitted -> Cancelled, then reverse the GL entry this invoice
        posted on submit (if any). Without this, a cancelled invoice leaves
        its Accounts Receivable/Sales Revenue entries live forever, silently
        overstating both — an accounting-correctness gap independent of
        reference-server parity, previously accepted as a known limitation
        (see CLIENT_GUIDE.md, Known limitations). Idempotent the same way
        post_journal_entry is: reverse_journal_entry no-ops if already run."""
        super().cancel(user)
        self.reverse_journal_entry(user)

    def post_journal_entry(self, user=None):
        """Auto-create the balanced JournalEntry for this invoice:
        Dr Accounts Receivable / Cr Sales Revenue, both for final_amount.

        Idempotency guard mirrors VASStockMovement's source_* OneToOneField
        pattern in vas/models.py: JournalEntry.source_invoice is a OneToOne
        back-reference, so `hasattr(self, 'journal_entry')` is True once a
        line has been posted for this invoice, and a second call is a no-op.
        Simplification: this posts subtotal/GST as a single lump sum against
        two accounts rather than breaking GST out into its own GL line(s) —
        deliberately kept simple per the brief.
        """
        if hasattr(self, 'journal_entry'):
            return self.journal_entry
        entry = JournalEntry.objects.create(
            entry_date=self.invoice_date,
            description=f'Auto-posted on submit: Sales Invoice {self.invoice_number}',
            reference=self.invoice_number,
            reference_doctype='billing.Invoice',
            reference_docname=str(self.pk),
            created_by=user,
            source_invoice=self,
        )
        JournalEntryLine.objects.create(entry=entry, account='Accounts Receivable', debit=self.final_amount)
        JournalEntryLine.objects.create(entry=entry, account='Sales Revenue', credit=self.final_amount)
        return entry

    def reverse_journal_entry(self, user=None):
        """Post the mirror-image JournalEntry of post_journal_entry's
        Dr Accounts Receivable / Cr Sales Revenue, net-zeroing this
        invoice's GL impact on cancel. Idempotent: looks for an existing
        reversal by reference_docname + a distinct reference_doctype tag
        rather than relying on a second OneToOneField (an Invoice can only
        be cancelled once — DocStatusMixin.cancel already raises ValueError
        on a second call — but this guard keeps reverse_journal_entry safe
        to call standalone, e.g. from a future data-fix script)."""
        if not hasattr(self, 'journal_entry'):
            return None
        if JournalEntry.objects.filter(
            reference_doctype='billing.Invoice.cancel', reference_docname=str(self.pk)
        ).exists():
            return None
        original = self.journal_entry
        entry = JournalEntry.objects.create(
            entry_date=self.cancelled_at.date() if self.cancelled_at else self.invoice_date,
            description=f'Reversal on cancel: Sales Invoice {self.invoice_number}',
            reference=self.invoice_number,
            reference_doctype='billing.Invoice.cancel',
            reference_docname=str(self.pk),
            created_by=user,
        )
        for line in original.lines.all():
            JournalEntryLine.objects.create(
                entry=entry, account=line.account,
                debit=line.credit, credit=line.debit,
            )
        return entry
```

- [ ] **Step 4: Run the tests again to confirm they pass**

Run: `python manage.py test billing.tests.InvoiceCancelReversesJournalEntryTests -v 2`
Expected: both tests PASS.

- [ ] **Step 5: Run the full billing suite to confirm no regression**

Run: `python manage.py test billing`
Expected: all existing billing tests still pass (in particular `JournalEntryCreateTests`, unaffected since manually-created journal entries never set `reference_doctype='billing.Invoice'`).

- [ ] **Step 6: Update the tracking docs**

Mark this item `Fixed` in `docs/audit/DEVIATIONS.md`, and update `CLIENT_GUIDE.md` §9 (`Known limitations and accepted risks`) to remove the now-resolved "GL auto-posting doesn't reverse on invoice cancel" bullet (keep the still-true "Payment Reconciliation bulk-complete doesn't auto-post" half of that bullet, since this task only fixes the cancel-reversal half).

- [ ] **Step 7: Commit**

```bash
git add billing/models.py billing/tests.py docs/audit/DEVIATIONS.md CLIENT_GUIDE.md
git commit -m "fix: reverse the auto-posted GL entry when an invoice is cancelled"
```

**Repeat this Task-5 pattern (failing test -> minimal fix -> green -> update DEVIATIONS.md -> commit) once per remaining `Open` item in `docs/audit/DEVIATIONS.md`, in the ranked order the file lists them.**

---

## Task 6: Full regression run

**Files:** none (verification only)

- [ ] **Step 1: Run the Django unit test suite**

Run: `python manage.py test`
Expected: all 138+ tests pass (count will be 138 + however many were added in Task 5's fix cycles).

- [ ] **Step 2: Run the Playwright e2e suite**

Run: `python manage.py test e2e`
Expected: all 5 e2e flow files pass (`test_double_submit_guard`, `test_invoice_gl_flow`, `test_rc_handover_flow`, `test_sales_order_create_form`, `test_sales_order_flow`). If `Invoice GL Flow` covers cancel, confirm it still passes with Task 5's change; if it doesn't cover cancel, that's a real e2e gap — file it as a new `Open` item in `docs/audit/DEVIATIONS.md` rather than silently skipping it.

- [ ] **Step 3: Run the full-route smoke scripts**

Run: `python check_all.py` then `python run_full_test.py`
Expected: both report zero FAIL entries (matching the last recorded clean run in `test_results.json`/`qa_report.json`).

- [ ] **Step 4: Record the result**

Append a dated entry to `docs/audit/PARITY_SIGNOFF.md` (created in Task 8) — or, if Task 8 hasn't run yet, hold this result to include there directly.

---

## Task 7: Extend the walkthrough to Tiers 2–8 (repeat Task 3's procedure)

Repeat Task 3's exact procedure — pick reference fact, grep Django equivalent, classify Match/Deviation/Missing/Deliberate-difference/Descoped-tonight, fill the matrix row, commit — once per remaining priority tier:

- [ ] **Tier 2 — Billing/Payments/GL**: cross-check `reference_erp_spec/02_Payments.md`, `14_Receipts.md`, `19_GST_Tax_Reports.md`, `20_For_Payout_GST_Bill.md` against `billing/`. Commit: `git commit -m "audit: complete Tier 2 (Billing/Payments/GL) parity walkthrough"`.
- [ ] **Tier 3 — Service/Job Card pipeline**: cross-check `reference_erp_spec/08_Maintenance_Vehicle.md`, `11_Service_Enquiry.md`, `12_Follow_Ups.md` against `service/`. Commit: `git commit -m "audit: complete Tier 3 (Service/Job Card) parity walkthrough"`.
- [ ] **Tier 4 — Spares**: cross-check `reference_erp_spec/13_Spares_Purchase.md`, `10_Spares_Stock_Reconciliation.md` against `spares/`. Commit: `git commit -m "audit: complete Tier 4 (Spares) parity walkthrough"`.
- [ ] **Tier 5 — RTO/Exchange**: cross-check `reference_erp_spec/22_Exchange.md` and the RTO-relevant sections of `18_Sales_Form.md` against `rto/`. Commit: `git commit -m "audit: complete Tier 5 (RTO/Exchange) parity walkthrough"`.
- [ ] **Tier 6 — Used Vehicles**: cross-check `reference_erp_spec/06_Used_Vehicle_Purchase.md`, `07_Used_Vehicle_Sale.md`, `15_Used_Vehicle_Sale_Master.md` against `used_vehicles/`. Commit: `git commit -m "audit: complete Tier 6 (Used Vehicles) parity walkthrough"`.
- [ ] **Tier 7 — VAS**: cross-check the VAS-relevant entries in `reference_erp_spec/26_Master.md`/`23_Masters.md` against `vas/`. Commit: `git commit -m "audit: complete Tier 7 (VAS) parity walkthrough"`.
- [ ] **Tier 8 — Masters/Admin/Roles**: cross-check `reference_erp_spec/17_Settings.md`, `23_Masters.md`, `26_Master.md` against `masters/` and `accounts/`. Commit: `git commit -m "audit: complete Tier 8 (Masters/Admin) parity walkthrough"`.

**Time-box rule:** after each tier, re-run Task 4's extraction step to refresh `docs/audit/DEVIATIONS.md`, then decide whether to keep walking tiers or switch to fixing what's already queued — money/stock-integrity deviations always outrank finishing every tier. If the clock runs out mid-list, stop and mark every remaining tier `Descoped-tonight` in `docs/audit/DEVIATIONS.md` with the reason "time-boxed for tonight's delivery — see PARITY_MATRIX.csv rows still blank for `<tier>`" — never leave it silently implied.

---

## Task 8: Final sign-off

**Files:**
- Create: `docs/audit/PARITY_SIGNOFF.md`

- [ ] **Step 1: Write the sign-off document**

```markdown
# Parity Audit Sign-Off — 2026-07-20

## What was audited
<list the tiers actually walked tonight, with commit refs from Tasks 3/7>

## Matrix summary
<counts: N rows Match, N Deviation-now-Fixed, N Deliberate-difference, N Descoped-tonight — pull straight from docs/audit/PARITY_MATRIX.csv>

## Bugs found and fixed tonight
<one line per Task-5-cycle fix, each with its commit hash and the test that proves it>

## Deliberate differences (not bugs)
<carry forward the still-valid ones from PRODUCTION_DELIVERY_REPORT.md §9 item 11 (Customer Vehicle), plus the two reference-app bugs from Task 3 Step 2>

## Explicitly not covered tonight
<the Descoped-tonight rows from docs/audit/DEVIATIONS.md, each with its reason>

## Regression status
<Task 6's results: unit tests, e2e suite, smoke scripts — all green, with counts>

## How to verify this yourself
Open docs/audit/PARITY_MATRIX.csv, filter to `status != Match`, and check each
row's `evidence` column against the referenced file/line or test name.
```

- [ ] **Step 2: Commit**

```bash
git add docs/audit/PARITY_SIGNOFF.md
git commit -m "audit: publish parity sign-off for tonight's delivery"
```

---

## Self-Review Notes

- **Spec coverage:** Task 1 validates the existing 429-doctype baseline; Task 2 turns it into a checkable ledger; Tasks 3/7 walk all 8 priority tiers (every reference module group in `reference_erp_spec/00-26`); Task 4 makes gaps trackable instead of narrative; Task 5 is the repeatable fix pattern; Task 6 is the regression gate; Task 8 is the client-facing evidence artifact. The 141 "not in main nav" doctypes (`27_not_in_main_nav.md`) are explicitly out of tonight's priority order per Global Constraints and must land in `docs/audit/DEVIATIONS.md` under "Not covered this pass," not be silently skipped.
- **Placeholder scan:** the one open-ended step (Task 7's tier list) is a repeatable, fully-specified procedure with a worked instance in Task 3 and explicit file targets per tier — not a vague "handle appropriately."
- **Type/name consistency:** `Invoice.cancel`/`reverse_journal_entry` signatures match `DocStatusMixin.cancel(self, user)`; `JournalEntry`/`JournalEntryLine` field names (`account`, `debit`, `credit`, `reference_doctype`, `reference_docname`) match the existing `billing/models.py:412-478` definitions exactly, confirmed by reading the file before writing this plan, not assumed.

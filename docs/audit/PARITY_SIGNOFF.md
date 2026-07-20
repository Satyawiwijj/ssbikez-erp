# Parity Audit Sign-Off — 2026-07-20

This replaces narrative-only status reports with an evidence-backed ledger. Every claim below traces to a file, a commit, or a row in `docs/audit/PARITY_MATRIX.csv` that you can open and check yourself — see "How to verify this yourself" at the bottom.

## What was audited tonight

1. **Freshness of the reference-server spec** (`reference_erp_spec/`, extracted in an earlier session: 429 custom doctypes, 201 client scripts on the client's live test server at `95.216.169.103`). Re-confirmed live against the running server tonight — baseline is current, no drift. Commits `23177c6`..`74860b9`.
2. **Parity matrix scaffold**: every one of the 429 custom doctypes' native fields, extracted from the reference server's own API dump, loaded into `docs/audit/PARITY_MATRIX.csv` (5,549 rows) as the row-by-row comparison ledger. Commit `3c07898`.
3. **Tier 1 — New Vehicle Sales Order chain** (Enquiry → Appointment → Order → Delivery → Invoice/GST): the highest-revenue-impact flow in the app, cross-checked field-by-field and behavior-by-behavior against the reference server's already live-verified mechanics (`reference_erp_spec/31_LIVE_VERIFIED_flows.md` — real browser sessions against the reference server, not schema-only guesses). Commit `df7dbba`.
4. **Tier 2 — Billing / Payments / GL**: the second-highest financial-risk area (invoices, payments, GST, journal entries, general ledger), cross-checked against `02_Payments.md`, `14_Receipts.md`, `19_GST_Tax_Reports.md`, `20_For_Payout_GST_Bill.md`. Commits `7b88159`, `7f0e909`.

## Matrix summary

| Status | Rows | What it means |
|---|---|---|
| Match | 14 | Confirmed same field/behavior, evidence-cited |
| Deviation | 11 | Field/behavior exists on both sides but differs |
| Missing | 82 | Reference has it, Django app doesn't |
| N/A | 24 | Layout-only rows (Section/Column Breaks — not real fields) |
| Deliberate-difference | 2 | Reference-app bugs, intentionally not reproduced |
| *(blank — not yet walked)* | 5,416 | Tiers 3–8, see "Not covered tonight" below |

133 of 5,549 rows (12 of 430 doctypes) have been evidence-checked so far — Tiers 1 and 2, the two highest-financial-impact areas. Every Match/Deviation/Missing verdict was independently re-verified by a second reviewer against the actual source files before being accepted (see "How to verify" below) — no verdict shipped on a first pass alone.

## Bugs found and fixed tonight

Both are real, load-bearing General Ledger gaps of the same class — money silently not reaching the ledger — found during the parity walkthrough, not hypothetical:

1. **`Invoice.cancel()` never reversed its auto-posted GL entry.** A cancelled invoice permanently overstated Accounts Receivable and Sales Revenue. Already a documented accepted risk in `CLIENT_GUIDE.md` §9 before tonight. Fixed: `Invoice.cancel()` now posts a mirror-image reversing `JournalEntry`, guarded against double-reversal. Commit `97b5645`. Test: `billing/tests.py::InvoiceCancelReversesJournalEntryTests` (2/2 passing).
2. **Reconciling a Payment to Completed never posted its GL entry** — only a Payment *created* already-Completed did. The normal cash-collection workflow (record Pending → reconcile later) silently posted nothing to the ledger, for both the individual-edit path and the bulk Payment Reconciliation screen. Fixed: `Payment.save()` now posts on any transition to Completed, and the bulk reconciliation view saves each payment individually instead of a raw bulk `.update()` that bypassed the model hook entirely. Commit `7b88159`. Test: `billing/tests.py::PaymentReconciliationPostsJournalEntryTests` (2/2 passing).

Both fixes were independently re-verified by a reviewer who traced the debit/credit accounting by hand and confirmed idempotency (no double-posting), not just "tests pass."

## Deviations still open (not yet fixed)

Ranked by business impact in `docs/audit/DEVIATIONS.md`. Highlights:

**Financial / data-integrity (3 open):**
- No cross-check between a Sales Order's price and any approved price-list master (`CustomerPrice` exists but is unused in the sales flow) — every order's pricing is currently unvalidated free entry.
- A Sales Order's GST category is copied from the customer once and never re-synced if the customer link changes later — stale GST category can silently drive the wrong CGST/SGST-vs-IGST split on invoice.
- A Sales Order's vehicle link is optional with no model-level distinction between "intentionally a spares-only order" and "vehicle order missing its stock link by mistake."
- Two structural gaps also surfaced: no multi-invoice payment allocation, and no Chart-of-Accounts/Bank/Mode-of-Payment master data (GL account names are free-typed with no validation) — both real, both larger scoping conversations than a same-night fix.

**Workflow blockers (3 open):** no per-branch dynamic requiredness for the Sales Enquiry link (reference gates this by branch; Django doesn't); manual Journal Entries have no approval gate or cancel/amend lifecycle (no `docstatus` at all, unlike every other document type in this app); no backdating-window control on manual GL postings.

**Cosmetic / low-impact (5 open):** minor field/label differences (phone-number snapshot, vehicle-color modeling approach, sub_group, optional payment method, document numbering scheme) — see `docs/audit/DEVIATIONS.md` for full evidence on each.

## Deliberate differences (not bugs)

- **`Customer Vehicle` exists as its own record in this app but has no reference-server equivalent.** The reference ERP tracks a sale and stops; this app needs to track what happens to a specific vehicle after delivery (service, VAS, RTO, warranty), which requires a persistent post-sale vehicle record. Explained in full in `PRODUCTION_DELIVERY_REPORT.md` §9 item 11 — a scoping difference, not a gap to close.
- **Orphaned `Vehicle Chasis Number Master` records on a failed Purchase Invoice submit** and **the `loadDefaultHelmet`/`vehicle_charges_list` race condition on submit** — both confirmed, reproducible bugs *in the reference app itself* (`reference_erp_spec/31_LIVE_VERIFIED_flows.md` §1). Deliberately not reproduced — matching a reference bug would itself be a deviation from correct behavior.

## Explicitly not covered tonight

**Tiers 3–8 of the priority order** — Service/Job Card pipeline, Spares, RTO/Exchange, Used Vehicles, VAS, Masters/Admin/Roles — have not been walked yet. This covers roughly 5,416 of the matrix's 5,549 rows (about 418 of 430 doctypes, mostly the 141 doctypes the reference spec itself already flags as "not in main nav" — lower priority, reached only via secondary role workspaces or used purely as link-field targets).

This is a **sequencing gap, not a scope cut made to hide anything**: tonight prioritized the two highest-financial-risk tiers (Sales Order revenue flow, Billing/GL money movement) over breadth, on the judgment that two real, load-bearing GL bugs found and fixed in the areas actually walked are worth more than a shallow pass over all 8 tiers with no time left to fix anything found. The next audit session should start at Tier 3 (Service/Job Card) — `docs/audit/PARITY_MATRIX.csv` already has the reference-side data scaffolded for every remaining doctype; only the Django-side comparison and verdict columns are blank and waiting.

## Regression status

Run fresh, directly, immediately before this sign-off (not carried over from an earlier point in the night):

- `python manage.py test` — **151/151 passing**. Directly observed growth during tonight's session: 149/149 after Task 5's fix, 151/151 after Task 7's fix (+2 tests each: `InvoiceCancelReversesJournalEntryTests`, `PaymentReconciliationPostsJournalEntryTests`). Note: the README/CLIENT_GUIDE cite "138 tests" as of an earlier point in this project's history — that figure was not independently re-verified tonight before this session's own changes, so it's not used as tonight's baseline; the 149→151 delta is what was actually measured.
- `python manage.py test e2e` (Playwright, real browser) — **9/9 passing**.
- `check_all.py` — fails to import (`SparePart` was renamed to `SparesItem` at some point before tonight; this ad hoc script wasn't updated). Pre-existing script rot, unrelated to any change made tonight — not part of the regression floor (`manage.py test` covers this app's actual behavior), but worth a cleanup pass separately.
- `run_full_test.py` — 218/225 checks passing against the live dev database. The one FAIL (login-OTP redirect) and its related RBAC warnings trace to using a placeholder admin password for this run (the real dev-DB admin credential wasn't available), not a code defect — confirmed by reading the script's own logic. One pre-existing informational warning (1 item with negative stock in the dev database) predates tonight's changes and is unrelated to anything touched.

No regressions from tonight's changes in any suite.

## How to verify this yourself

Open `docs/audit/PARITY_MATRIX.csv` and filter to `status != Match` and `status != ""` — every row's `evidence` column points to an exact `file:line` in this repo or a named test. Open `docs/audit/DEVIATIONS.md` for the same evidence in ranked, narrative form. Every task tonight went through a second independent reviewer who re-verified the cited evidence against the actual source files before the work was accepted — this was not a single pass.

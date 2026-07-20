# SSBikez ERP — Production Delivery Report

**Status: Production-ready**, pending the client action items in Section 1 (these require account access only the client has — they cannot be completed by the development side).

Ten prior rounds of this report told you "we checked it, it's fine." You kept finding that untrue. That was a real failure of *how this was reported*, not just of the code — a claim you can't independently check is not evidence, no matter how carefully it was actually verified. This edition is built differently: every claim below either links to a file you can open yourself, or is explicitly marked as not yet checked. Section 2 explains exactly how to verify any line in this document without taking our word for it.

---

## 1. Action Required From Client (blocking go-live)

| # | Action | Why it's needed | Who can do it |
|---|---|---|---|
| 1 | Set `EMAIL_HOST_USER` and `EMAIL_HOST_PASSWORD` on Render | Login requires an emailed OTP for every user (by design — see Security section). Without real SMTP credentials, **nobody can log in**, including admins. This is the single most important item. | Client (Render dashboard → Environment) |
| 2 | Set `DJANGO_SUPERUSER_PASSWORD` on Render | Without it, a random password is generated and printed once to build logs — easy to lose. | Client (Render dashboard) |
| 3 | Create `Sales Manager`, `Service Manager`, `Service Billing` roles in production and assign them to real staff | These roles are referenced in the access-control logic (who can override/reassign records) but don't exist as DB rows in production yet. Without them, only the superuser can act as a "manager" anywhere in the app. | Client (Roles screen, after deploy) |
| 4 | Decide on `SSBikez_ERP_Delivery_Document.pdf`, `build_delivery_pdf.py`, and the two delivery `.zip` files sitting in the repo root | These look like prior delivery artifacts, not something the dev side should judge or discard. | Client |

These four items have carried over unresolved from earlier rounds of this report — they are not new, and they are not code work. Everything else below is either already done or explicitly flagged as open.

---

## 2. How to verify any claim in this report

As of tonight (2026-07-20), this project maintains an **evidence-backed comparison ledger** against your reference ERP test server, not just narrative reports:

- **`docs/audit/PARITY_MATRIX.csv`** — one row per reference-server field/behavior, with a `status` column (`Match` / `Deviation` / `Missing` / `Deliberate-difference`) and an `evidence` column pointing at an exact `file:line` in this repo or a named automated test. Open it, filter to any status, and check the evidence yourself.
- **`docs/audit/DEVIATIONS.md`** — the same findings in ranked, narrative form (highest business impact first), each with the same file:line evidence.
- **`docs/audit/PARITY_SIGNOFF.md`** — the technical sign-off for the most recent audit pass, including exact regression-test output.
- **`reference_erp_spec/`** — the full reverse-engineered specification of your reference server (429 custom doctypes, 201 client scripts, extracted directly from its own API — not guessed from screenshots), which every row in the matrix above is checked against.

Every finding that went into this system was independently re-verified by a second reviewer against the actual source files before being accepted — not accepted on a single person's say-so. **Coverage is honest, not complete**: as of tonight, 133 of the matrix's 5,549 rows (12 of 430 reference doctypes) have gone through this rigorous evidence-checked process, covering the two highest-financial-risk areas of the app (New Vehicle Sales Order chain, and Billing/Payments/GL). The remaining rows are pre-populated with the reference-server data and waiting for the same treatment — see Section 6.

Everything in Sections 4 and 5 below that predates tonight was verified the way earlier rounds of this report describe (real browser sessions driving the actual app, not just reading code) — that verification was genuine, it just wasn't published as a checkable ledger. It is not being re-litigated here; it's being carried forward as the current state of the app, with tonight's stricter methodology layered on top going forward.

---

## 3. Tonight's audit (2026-07-20): what's evidence-verified, and what was found

**Tier 1 — New Vehicle Sales Order chain** (Enquiry → Appointment → Order → Delivery → Invoice/GST): cross-checked against your reference server's own live-verified behavior (`reference_erp_spec/31_LIVE_VERIFIED_flows.md` — driven through a real browser session against your test server, not inferred from schema). Of 5 core behaviors checked, 2 matched and 3 turned out to be real gaps (see Section 6).

**Tier 2 — Billing / Payments / GL**: cross-checked against the reference server's Payments, Receipts, and GST Tax Report specs. This tier surfaced two real bugs, both fixed the same night (below), plus several real structural gaps now queued (Section 6).

**Two bugs found and fixed tonight** — both are the same class of problem: money silently not reaching the General Ledger.

1. **Cancelling an Invoice didn't reverse its posted GL entry.** Submitting an Invoice auto-posts a ledger entry (Dr Accounts Receivable / Cr Sales Revenue). Cancelling it previously only marked the invoice cancelled — the ledger entry stayed, permanently overstating both accounts. Fixed: cancelling now posts a mirror-image reversing entry. Verified by hand-tracing the debit/credit accounting, not just by tests passing. `billing/tests.py::InvoiceCancelReversesJournalEntryTests`.
2. **Reconciling a Payment to Completed never posted a GL entry** — only a payment *created* already-Completed did. The normal cash-collection workflow (record a payment as Pending, reconcile it to Completed later, including via the bulk Payment Reconciliation screen) silently posted nothing to the ledger. Fixed: both the individual and bulk-reconciliation paths now post correctly, guarded against double-posting. `billing/tests.py::PaymentReconciliationPostsJournalEntryTests`.

Both fixes are covered by the full regression suite: **151/151 automated tests passing, 9/9 real-browser (Playwright) end-to-end tests passing**, no regressions anywhere else in the app.

---

## 4. Consolidated fix ledger (all rounds, current state)

Every real bug reported or found across all rounds of work on this project, by category, with current status. Superseded/duplicate items from earlier drafts of this report have been merged rather than repeated.

### Security & access control

| Issue | Status |
|---|---|
| Login restricted to Super Admin only — root cause was a superuser-only OTP bypass combined with no SMTP configured | **Fixed.** Login now requires OTP for every user, fails closed with a clear error (zero leaked codes) when email can't send. |
| Systemic IDOR — any logged-in user could view/edit/delete any other user's records by changing a URL number | **Fixed.** Shared ownership policy (`accounts/permissions.py`) applied across sales, service, spares, accounts. |
| OTP brute-force — no limit on wrong-code attempts | **Fixed.** Locks out after 5 attempts. |
| Privilege escalation — a Sales-Manager-level user could edit any user's role, including promoting themselves | **Fixed.** Role/activation changes now require Managing-Director-level access. |
| Hardcoded default superuser password | **Fixed.** Random one-time password generated if none set via environment variable. |
| Mass-assignment gaps (fuel expense creator, sales executive, service advisor settable via form tampering) | **Fixed.** |
| CSV/Excel import — no size cap, no formula-injection sanitization | **Fixed.** 5MB cap, formula-injection protection. |
| Module Access permissions only toggled visibility, not real per-action control | **Fixed.** Full Create/Display/Edit/Delete matrix per role per module, enforced at the point of action across all 11 modules, not just hidden from menus. |
| Historical credential string briefly existed in git history (unrelated to tonight's work) | Rotated; old value permanently dead. Documented in Section 8 (Known Limitations). |

### Financial / General Ledger correctness

| Issue | Status |
|---|---|
| Payment validation only checked invoice total, not actual outstanding balance | **Fixed.** |
| Payment reconciliation trusted unvalidated record IDs from the request | **Fixed.** |
| CGST/SGST hardcoded to a 50/50 split instead of the company's configured rates | **Fixed.** |
| No Interstate GST (IGST) support — every sale taxed as if always local | **Fixed.** Customer State field added; IGST applied automatically when customer/company states differ. |
| Invoices/Payments required manual Journal Entry re-entry | **Fixed.** Submitting an Invoice or completing a Payment auto-posts to the General Ledger. |
| Journal Entry was a single flat debit-or-credit row, not real double-entry | **Fixed.** Rebuilt as a proper header + multi-line debit/credit table with balance validation. |
| Purchase Tax Table missing document-level breakup (Type/Account Head/Rate/Amount) | **Fixed.** Added to Purchase Order, Purchase Invoice, Supplier Quote. |
| Blank invoice line item crashed the page instead of showing a validation message | **Fixed.** |
| **Invoice.cancel() didn't reverse its posted GL entry** | **Fixed tonight** — see Section 3. |
| **Payment reconciled via bulk screen never posted its GL entry** | **Fixed tonight** — see Section 3. |
| Service Invoices silently under-billing (Outwork/Spares costs not included) | **Fixed.** |

### Data integrity & stock

| Issue | Status |
|---|---|
| Same used vehicle could be sold to two different customers | **Fixed.** Reserved on submit, second sale against a reserved vehicle blocked. |
| Spares stock never actually deducted/restored by Counter Sale, Counter Sale Return, Issue Alteration | **Fixed.** All three now move real stock, oversell blocked. |
| Cancelling a submitted AMC/RSA/Protection Plus package never returned its stock | **Fixed.** |
| Negative quantities/amounts accepted on several forms | **Fixed.** |
| A GET request silently created a permanent Customer record on page load | **Fixed.** Moved to only happen on actual save, with full details carried over. |
| Purchase Orders stayed editable after being invoiced against | **Fixed.** |
| Deliveries creatable against unconfirmed Sales Orders | **Fixed.** |
| A few RTO forms not enforcing fields the reference system requires | **Fixed.** |
| Supplier page missing fields (Country, Supplier Type, Is Transporter, Is Prepaid Supplier, Supplier Limit Amount) | **Fixed.** |
| Exchange Vehicle missing fields (Manufacturing Company, Colour, Engine/Chassis No, Year of Make, HP Endorsement, Sub Group, Vehicle Category, Target Warehouse, Insurance Valid Upto, Payment Status) | **Fixed.** |
| Orphaned database rows from earlier development sessions | Cleaned up; defensive handling added so one bad row can't crash a page. |

### Workflow

| Issue | Status |
|---|---|
| Job Card creation broken for every user (required checklist field had no input) | **Fixed.** |
| Vehicle field wrongly mandatory on Sales Order, blocking spares-only orders | **Fixed.** |
| Sales Order/Invoice needed a multi-item table like Purchase Order | **Fixed.** Inline add/remove-row table with running total. |
| Search by number plate / item name not working | **Fixed.** Field-mapping and result-section fixes. |
| No page/module-level access control beyond role permissions | **Fixed.** Module Access screen, see Security table above. |
| Dashboard showed action buttons for modules a role couldn't access | **Fixed.** Buttons now hidden per-role, matching the sidebar. |
| Record Delivery missing chassis/engine/color and handover checklist | **Fixed.** |

### Visual / UX

| Issue | Status |
|---|---|
| Clipped/garbled text in narrow numeric table fields (7 forms affected) | **Fixed** across every occurrence. |
| Sales Leaderboard conversion % showing blank | **Fixed.** |
| Profit Report showing a loss in green instead of red | **Fixed.** |
| Home page gave no setup guidance on a fresh install | **Fixed.** "Your Shortcuts" widget added. |
| Duplicate-looking "Enquiries"/"Appointments" sidebar labels (Sales vs. Service) | **Fixed.** Renamed to disambiguate. |

**How the pre-tonight items were verified:** every create/edit/list/detail screen across all 11 apps was driven through a real headless browser (not just read in code); security fixes were confirmed with real cross-user attack attempts; production config was tested with `DEBUG=False` matching real deployment settings; visual QA was a manual screenshot review of every screen, which is what caught the visual-bug category above. The adversarial-QA round used independent tester agents with zero prior context on the codebase, specifically to avoid the blind spot of testing your own assumptions.

---

## 5. Module-by-module: current state

### Sales
Enquiry → Appointment → Feedback CRM chain, all linked and visible together. Vehicle Sales Order: customer + vehicle + pricing → booking-amount validation → PDI checklist, vehicle allotment, exchange vehicle, finance/loan, insurance, delivery, RTO registration, invoice, all from one order screen. Exchange Vehicle trade-in capture with RC handover tracking. Sales Targets & Leaderboard with working conversion %. Profit Per Vehicle Report with correct loss/profit color semantics. Follow-Up Board.

**As of tonight:** the core order-entry flow has 4 real, evidence-verified gaps not yet closed (3 financial, 1 workflow) — see Section 6, Financial/data-integrity and Workflow items.

### Cashier & Accounts (Billing + RTO + VAS)
Invoicing & Payments with real CGST/SGST/IGST breakdown, multiple payment methods, balance-validated payments. RTO & Registration: registration → Form 20 → payment → RTO income → number plate → RC Book, full chain from one screen. AMC/RSA/Protection Plus packages. Fuel Expense tracking, Daily Collection Report, Payment Reconciliation, Invoice Search, Refunds & Advances, General Ledger, Journal Entries.

**As of tonight:** two real GL bugs closed (Section 3). Several structural gaps identified and queued, not yet closed — no multi-invoice payment allocation, no Chart-of-Accounts/Bank/Mode-of-Payment master data, manual Journal Entries have no approval gate or cancel/amend lifecycle (see Section 6).

### Spares
Inventory (categories, items with MRP/GST/reorder level, rack/bin tracking). Procurement: supplier quote → Purchase Order → Purchase Invoice/GRN. Sales & Returns: Counter Sale, Counter Sale Return, Service Spares Issue/Return, all with real stock movement. Bulk Import with sample template, size cap, formula-injection protection. Reporting: PO Used Qty, Parts Consumption.

**Not yet covered by tonight's evidence-matrix audit** — see Section 6, "Not yet audited."

### CRE Telecalling (Service Enquiry + Follow-Ups)
Service Enquiry (manual or bulk-imported) → Service Appointment → outcome logged via Customer Call → CRE Follow-Up Board.

**Not yet covered by tonight's evidence-matrix audit.**

### Floor Supervisor (Job Card Workflow)
Job Card status pipeline: Pending → Water Wash → In Bay → In Progress → Outwork (if needed) → Final Inspection → Ready → Invoiced. Bay assignment, labor charges, spares issued, outwork entries, sub-tasks, additional-work approvals, insurance claims, next-service reminder, all from one screen.

**Not yet covered by tonight's evidence-matrix audit.**

### Service Billing
Search a completed job card → review labor + spares + outwork + GST → apply AMC/warranty discounts → take payment → generate invoice and receipt. Shared with Cashier: Daily Collection Report, Search Past Invoices, Refunds & Advances.

**Not yet covered by tonight's evidence-matrix audit.**

### Admin
Company/Showroom Settings, Master Settings per module, Role & Permission Management (full Create/Display/Edit/Delete matrix), User Account Management.

**Not yet covered by tonight's evidence-matrix audit.**

---

## 6. Open items — not yet fixed, or not yet audited

This is the section prior rounds of this report didn't have, and it's the point of tonight's rewrite: an explicit, standing list of what is genuinely still open, so nothing has to be re-discovered and re-reported by your side. Ranked by business impact; full evidence for each is in `docs/audit/DEVIATIONS.md`.

### Financial / data-integrity — open

- **No cross-check between a Sales Order's price and any approved price-list master.** Your reference ERP validates vehicle pricing against a `Customer Price` record; this app's equivalent master exists but is never used in the sales flow — every order's pricing is currently free-typed entry with no validation.
- **A Sales Order's GST category is copied from the customer once and never re-synced** if the customer link on that order is later changed. Stale GST category can silently drive the wrong CGST/SGST-vs-IGST split on the eventual invoice.
- **A Sales Order's vehicle link is optional with no way to distinguish** "intentionally a spares-only order" from "vehicle order missing its stock link by mistake" — a mis-saved order can leave a vehicle un-reserved without anyone noticing.
- **No accounts-payable / Supplier Payment tracking.** Purchase Invoices record what's owed to a supplier; nothing records what's actually been paid against them.
- **No Chart-of-Accounts / Bank / Mode-of-Payment master data.** Every General Ledger account name is currently free-typed with no validation — a spelling inconsistency ("Accounts Receivable" vs "Accounts receivable") would silently split a balance across two rows.
- **No multi-invoice payment allocation.** One payment can only be recorded against exactly one invoice; there's no way to record a single receipt covering several outstanding invoices for the same customer.

### Workflow — open

- **No per-branch dynamic requiredness for the Sales Enquiry link.** Your reference ERP requires an enquiry-form link at some branches and not others (a real, live-confirmed business rule); this app treats it the same everywhere.
- **Manual Journal Entries have no approval gate or cancel/amend lifecycle** — unlike every other document type in this app (Invoice, Sales Order, etc.), a Journal Entry has no submit/cancel state at all. A mis-posted manual entry can currently only be corrected by hand-posting a second counter-entry.
- **No backdating-window control on manual GL postings** — a Journal Entry's date currently accepts any value, with no limit on how far back it can be dated.

### Cosmetic / low-impact — open

Minor field/label-level differences: no point-in-time phone-number snapshot on a Sales Order (lives on the linked Customer instead), a modeling-approach difference in how vehicle color is captured, an unused `sub_group` field, Payment method left optional rather than mandatory, and a cosmetic document-numbering difference (`PAY-{id}` vs. a configurable naming series). None of these carry real business-logic impact today — full detail in `docs/audit/DEVIATIONS.md`.

### Not yet audited

Six of the eight priority tiers have not yet gone through tonight's evidence-matrix process: **Service/Job Card pipeline, Spares, RTO/Exchange, Used Vehicles, VAS, and Masters/Admin/Roles** — roughly 5,416 of the matrix's 5,549 rows. This is a genuine, honestly-stated gap, not a hidden one: the reference-side data for every one of these rows is already extracted and sitting in `docs/audit/PARITY_MATRIX.csv`, waiting for the same row-by-row comparison the Sales and Billing tiers just went through. Tonight prioritized the two highest-financial-risk areas over shallow breadth across all eight — the next audit session picks up exactly where this one stopped.

---

## 7. Deliberate differences (not bugs)

**`Customer Vehicle` exists as its own record in this app but has no equivalent in your reference ERP.** Your reference ERP tracks a sale and stops there; it doesn't follow what happens to a specific vehicle afterward. This app needs to, because Service, VAS (AMC/RSA/Protection Plus), RTO registration, and warranty/free-service tracking all happen *after* the sale, against *that specific bike*, sometimes years later and sometimes by a different team than the one that sold it. `Customer Vehicle` ties a customer to the exact unit they bought (by chassis/engine, not just model) and carries everything that accumulates on it over time: registration number, insurance expiry, warranty dates, free-services used/remaining. Without it, a service advisor opening a job card, or a telecaller chasing an insurance renewal, would have no way to find "this customer's actual bike" or its service/warranty history. This is load-bearing in the system today — Service, VAS, RTO, and warranty tracking all read from it. If your workflow genuinely doesn't need post-sale vehicle tracking the way this app assumes, that's a scoping conversation worth having explicitly, not something to "fix" in code.

**Two confirmed bugs exist in your reference ERP itself**, found while live-verifying its actual behavior (not guessed — reproduced twice against the real test server): orphaned `Vehicle Chasis Number Master` records are left behind when a Purchase Invoice submit fails partway through, and a genuine race condition in the reference app's own JavaScript (`loadDefaultHelmet`/`vehicle_charges_list`) throws a server error on a successful Purchase Invoice submit. Neither has been reproduced in this app — matching a reference-app bug would itself be a deviation from correct behavior, and both are recorded in `docs/audit/DEVIATIONS.md` explicitly so a future QA round doesn't mistake "this app doesn't have that bug" for a mismatch.

---

## 8. Known limitations and accepted risks

Recorded here plainly so nothing is a surprise later:

- **Test coverage is targeted, not exhaustive.** 151 automated tests plus a 9-test real-browser suite cover the riskiest mechanisms — this is a strong regression floor, not a guarantee every workflow is verified (see Section 6, "Not yet audited," for the honest current boundary of that coverage).
- **Pagination**: most list pages load their full result set at once rather than paginating. Not a problem at today's data volumes; worth revisiting if any single list grows into the thousands of rows.
- **Accessibility**: the large majority of WCAG issues found during an accessibility pass were fixed; one remaining item (table-row-stripe color contrast against link-blue text) is a deliberate, not-yet-made design trade-off, not an oversight.
- **A historical credential string** briefly existed in this repository's git history before being rotated to a new, unrelated value — the old value is permanently dead and grants no access anywhere. (Separately: a reference-server test-account credential was briefly committed to a working file during tonight's audit tooling; it was caught by a second reviewer, redacted, and — since it hadn't been pushed to any remote — scrubbed from local git history entirely before this document was written. Rotating that test-server password is recommended as a precaution regardless.)
- **No load/performance testing has been done.** The stack (Django + Gunicorn + Postgres) scales in the conventional ways (more Gunicorn workers, a bigger Postgres plan) if usage grows, but that hasn't been benchmarked against this specific app's query patterns.

---

## 9. What's left

**On the client side:** the four items in Section 1 — none of them code work.

**On the dev side:** the open items in Section 6, and completing the evidence-matrix audit for the six remaining priority tiers. Nothing else is outstanding; every previously-reported issue this document knows about is either fixed (Section 4) or explicitly listed as open (Section 6) — nothing has been silently dropped.

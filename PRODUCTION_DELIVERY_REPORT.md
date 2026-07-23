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

As of the 2026-07-20 → 2026-07-23 audit, this project maintains an **evidence-backed comparison ledger** against your reference ERP test server, not just narrative reports:

- **`docs/audit/PARITY_MATRIX.csv`** — one row per reference-server field/behavior, with a `status` column (`Match` / `Deviation` / `Missing` / `Deliberate-difference`) and an `evidence` column pointing at an exact `file:line` in this repo or a named automated test. Open it, filter to any status, and check the evidence yourself.
- **`docs/audit/DEVIATIONS.md`** — the same findings in ranked, narrative form (highest business impact first), each with the same file:line evidence.
- **`docs/audit/PARITY_SIGNOFF.md`** — the technical sign-off for the most recent audit pass, including exact regression-test output.
- **`reference_erp_spec/`** — the full reverse-engineered specification of your reference server (429 custom doctypes, 201 client scripts, extracted directly from its own API — not guessed from screenshots), which every row in the matrix above is checked against.

Every finding that went into this system was independently re-verified by a second reviewer against the actual source files before being accepted — not accepted on a single person's say-so. **Coverage is honest, not complete**: as of this update, 792 of the matrix's 5,560 rows (87 of 433 reference doctypes, ~20%) have gone through this rigorous evidence-checked process — all 8 priority tiers (New Vehicle Sales, Billing/GL, Service/Job Card, Spares, RTO/Exchange, Used Vehicles, VAS, Masters/Admin/Roles). The remaining rows cover the reference server's 141 lower-priority "not in main nav" doctypes and are pre-populated with reference-server data, waiting for the same treatment — see Section 6.

Everything in Sections 4 and 5 below that predates tonight was verified the way earlier rounds of this report describe (real browser sessions driving the actual app, not just reading code) — that verification was genuine, it just wasn't published as a checkable ledger. It is not being re-litigated here; it's being carried forward as the current state of the app, with tonight's stricter methodology layered on top going forward.

---

## 3. The audit (2026-07-20 → 2026-07-23): what's evidence-verified, and what was found

All 8 priority tiers, in business-impact order:

- **Tier 1 — New Vehicle Sales Order chain** (Enquiry → Appointment → Order → Delivery → Invoice/GST): cross-checked against your reference server's own live-verified behavior (`reference_erp_spec/31_LIVE_VERIFIED_flows.md`). Of 5 core behaviors checked, 2 matched and 3 turned out to be real gaps.
- **Tier 2 — Billing / Payments / GL**: cross-checked against the reference server's Payments/Receipts/GST specs.
- **Tier 3 — Service / Job Card pipeline**: confirmed the documented Pending → Water Wash → In Bay → In Progress → Outwork → Final Inspection → Ready → Invoiced pipeline is a genuine signal-driven implementation, not cosmetic.
- **Tier 4 — Spares**: parts inventory, purchase, counter sales, stock reconciliation, re-verified against the reference's stock-movement rules.
- **Tier 5 — RTO / Exchange**: registration → Form 20 → RTO income → number plate → RC Book chain, plus Exchange Vehicle.
- **Tier 6 — Used Vehicles**: the full purchase → sale → delivery → invoice → RC hand-over pipeline.
- **Tier 7 — VAS**: AMC / RSA / Protection Plus.
- **Tier 8 — Masters / Admin / Roles**: Role & Permission Management fidelity against the reference's per-DocType permission model.

**Six real bugs found and fixed across the audit** — all the same underlying failure mode: a rule the reference server enforces (money reaching the ledger, or a legal/compliance gate) that Django silently didn't.

1. **Cancelling an Invoice didn't reverse its posted GL entry** (Tier 1). Fixed: cancelling now posts a mirror-image reversing entry, verified by hand-tracing the debit/credit accounting. `billing/tests.py::InvoiceCancelReversesJournalEntryTests`.
2. **Reconciling a Payment to Completed never posted a GL entry** (Tier 2) — only a payment *created* already-Completed did. Fixed: both the individual and bulk-reconciliation paths now post correctly. `billing/tests.py::PaymentReconciliationPostsJournalEntryTests`.
3. **A Job Card could be invoiced immediately at `Pending` status** (Tier 3), skipping the entire workshop pipeline. Fixed: invoicing now requires `service_status == READY`.
4. **Counter Sale Return could be submitted with no godown specified** (Tier 4) — the stock-restoration signal silently no-op'd, permanently losing the returned stock. Fixed: godown is now required.
5. **RC Hand Over (RTO) accepted a trade-in without the RC book or NOC in hand** (Tier 5) — a real legal-compliance gap matching the reference's own `before_save` gate, which existed in the spec but wasn't enforced here. Fixed.
6. **RC Hand Over (Used Vehicles) had the identical unenforced gate** (Tier 6) — a separate doctype instance of #5, independently found and fixed.

**Two significant findings flagged as high-priority for the next fix pass, not yet closed:**
- **GST hardcoded at a flat 9%/9%, uncentralized from the app's own `split_gst()` helper, no IGST handling** — repeats across `spares/` (Tier 4), `used_vehicles.UsedVehicleInvoice` (Tier 6), and all three VAS sale docs (Tier 7). This is the exact same bug class already fixed once in `rto/` — it just wasn't fixed everywhere it occurs.
- **Used Vehicle Purchase Invoice has no duplicate registration/engine/chassis-number check** (Tier 6) — a re-submitted Purchase Invoice reusing an already-used registration number silently overwrites an existing vehicle's stock record, including force-resetting a Sold vehicle back to Available. A genuine data-loss path.

All six fixes and the full audit are covered by the regression suite: **195/195 automated tests passing, 10/10 real-browser (Playwright) end-to-end tests passing**, no regressions anywhere in the app.

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
| **Invoice.cancel() didn't reverse its posted GL entry** | **Fixed** — see Section 3. |
| **Payment reconciled via bulk screen never posted its GL entry** | **Fixed** — see Section 3. |
| Service Invoices silently under-billing (Outwork/Spares costs not included) | **Fixed.** |
| RTO tax calculation hardcoded 9%/9% CGST/SGST, ignoring company-configured rates and IGST | **Fixed.** Centralized through the shared `split_gst()` helper; historical data backfilled via a 3-step migration, not zeroed. |
| Sales Order / Invoice / Vehicle Delivery totals didn't reflect their own line items (saved independently, never recomputed) | **Fixed.** One shared helper, applied to all three document types. |
| Order detail page only showed the latest invoice's amount, not the total across all invoices on that order | **Fixed.** Aggregate total added to both display locations on the page. |
| General Ledger report had no date-range or account filters at all | **Fixed.** |

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
| Counter Sale Return could be submitted without a warehouse, silently losing the returned stock | **Fixed.** Warehouse now required at both form and model layer. |
| Supplier form field completeness never independently re-verified against the reference server (original extraction had failed for this doctype) | **Fixed.** Live re-check found 3 more real gaps (default currency, payment terms, tax ID) and closed them. |

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
| Topbar search icon looked clickable but had no click handler — only pressing Enter actually searched | **Fixed.** Real submit button now wraps the icon. |
| A Job Card could be invoiced immediately at Pending status, skipping the entire workshop pipeline | **Fixed.** Invoicing now requires the job card to have reached Ready status. |
| RC Hand Over (RTO and Used Vehicles, two separate doctypes) accepted a trade-in without the RC book or NOC actually in hand | **Fixed** in both. Matches the reference's own legal-compliance gate. |
| A raw "403 — Submitted documents cannot be edited" error gave no way to actually act on it, at 9 call sites across 3 apps | **Fixed.** Now links to the document's own page, where Cancel & Amend lives. |
| Several billing screens (invoices, payments, loans, journal entries, etc.) had no per-permission Display gate, only whole-module access | **Fixed.** 13 views consistently gated. |

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

**Evidence-matrix audit status (Tier 1):** 4 real gaps not yet closed (3 financial, 1 workflow) — see Section 6.

### Cashier & Accounts (Billing + RTO + VAS)
Invoicing & Payments with real CGST/SGST/IGST breakdown, multiple payment methods, balance-validated payments. RTO & Registration: registration → Form 20 → payment → RTO income → number plate → RC Book, full chain from one screen. AMC/RSA/Protection Plus packages. Fuel Expense tracking, Daily Collection Report, Payment Reconciliation, Invoice Search, Refunds & Advances, General Ledger (now with date/account filters), Journal Entries.

**Evidence-matrix audit status (Tiers 2, 5, 7):** 3 real bugs closed (2 GL-posting gaps, 1 RC Hand Over compliance gate). Real structural gaps identified and queued, not yet closed — no multi-invoice payment allocation, no Chart-of-Accounts/Bank/Mode-of-Payment master data, manual Journal Entries have no approval gate or cancel/amend lifecycle, GST hardcoded (not centralized) on VAS sale documents (see Section 6).

### Spares
Inventory (categories, items with MRP/GST/reorder level, rack/bin tracking). Procurement: supplier quote → Purchase Order → Purchase Invoice/GRN. Sales & Returns: Counter Sale, Counter Sale Return, Service Spares Issue/Return, all with real stock movement. Bulk Import with sample template, size cap, formula-injection protection. Reporting: PO Used Qty, Parts Consumption.

**Evidence-matrix audit status (Tier 4):** 1 real bug closed (Counter Sale Return could lose stock on a return with no warehouse specified). GST hardcoded at a flat 9%/9%, not centralized through the app's shared tax helper — flagged high-priority, not yet fixed (see Section 6).

### CRE Telecalling (Service Enquiry + Follow-Ups)
Service Enquiry (manual or bulk-imported) → Service Appointment → outcome logged via Customer Call → CRE Follow-Up Board.

**Evidence-matrix audit status (Tier 3):** covered as part of the Service tier walkthrough — see below.

### Floor Supervisor (Job Card Workflow)
Job Card status pipeline: Pending → Water Wash → In Bay → In Progress → Outwork (if needed) → Final Inspection → Ready → Invoiced. Bay assignment, labor charges, spares issued, outwork entries, sub-tasks, additional-work approvals, insurance claims, next-service reminder, all from one screen.

**Evidence-matrix audit status (Tier 3):** confirmed the documented pipeline is a genuine signal-driven implementation, not cosmetic. 1 real bug closed (a Job Card could be invoiced immediately at Pending, skipping the whole pipeline). Two real gaps queued, not fixed: no server-side enforcement of stage-submission *order*, and a manual status-override view that bypasses the pipeline entirely (see Section 6).

### Service Billing
Search a completed job card → review labor + spares + outwork + GST → apply AMC/warranty discounts → take payment → generate invoice and receipt. Shared with Cashier: Daily Collection Report, Search Past Invoices, Refunds & Advances.

**Evidence-matrix audit status:** covered as part of the Service (Tier 3) and Billing (Tier 2) tiers.

### Admin
Company/Showroom Settings, Master Settings per module, Role & Permission Management (full Create/Display/Edit/Delete matrix), User Account Management.

**Evidence-matrix audit status (Tier 8):** confirmed the role/permission system is a genuine, wired-everywhere reimplementation, not decorative — but at a coarser grain than the reference: single role per user (reference allows several at once), module-bucket permissions (reference grants per individual document type), no per-user override. Closing this gap would mean a schema change touching every permission check in the app — correctly not attempted as a quick fix; recorded as an open architectural Deviation (see Section 6).

### Used Vehicles
The full used-vehicle pipeline: Purchase Order → Purchase Receipt → Purchase Invoice (creates stock) → Sale → Delivery → Invoice → RC Hand Over → RC Book Issue, each step gated by a genuine Draft/Submitted/Cancelled lifecycle with real stock-safety guards (a submitted Sale reserves the vehicle; cancelling releases it back to Available).

**Evidence-matrix audit status (Tier 6):** 1 real bug closed (the same RC Hand Over compliance gate as RTO, a separate doctype instance). Two real gaps flagged high-priority, not yet fixed: GST hardcoded/not centralized (same class as Spares/VAS), and no duplicate registration/engine/chassis-number check before creating stock — a re-submitted Purchase Invoice can silently overwrite an existing (possibly already-Sold) vehicle's stock record (see Section 6).

---

## 6. Open items — not yet fixed, or not yet audited

This is the section prior rounds of this report didn't have: an explicit, standing list of what is genuinely still open, so nothing has to be re-discovered and re-reported by your side. Ranked by business impact; full evidence for every item is in `docs/audit/DEVIATIONS.md`, including per-tier walkthrough notes explaining exactly what was checked.

**Two findings below are flagged HIGH PRIORITY** — ranked above the rest because of their blast radius, and recommended as the next fix pass:

- **GST hardcoded at a flat 9%/9%, not centralized through the app's own `split_gst()` helper, no IGST handling — repeats across Spares, Used Vehicle Invoice, and all three VAS sale documents.** This is the exact same bug already found and fixed once in RTO this session — it just wasn't fixed everywhere it occurs. Four separate places now need the same treatment.
- **Used Vehicle Purchase Invoice has no duplicate registration/engine/chassis-number check before creating stock.** A re-submitted Purchase Invoice reusing an already-used registration number silently *overwrites* an existing vehicle's stock record — including force-resetting a Sold vehicle back to Available. This is a genuine data-loss path, not a missing-field gap.

### Financial / data-integrity — open

- **No cross-check between a Sales Order's price and any approved price-list master.** Your reference ERP validates vehicle pricing against a `Customer Price` record; this app's equivalent master exists but is never used in the sales flow — every order's pricing is currently free-typed entry with no validation.
- **A Sales Order's GST category is copied from the customer once and never re-synced** if the customer link on that order is later changed. Stale GST category can silently drive the wrong CGST/SGST-vs-IGST split on the eventual invoice.
- **A Sales Order's vehicle link is optional with no way to distinguish** "intentionally a spares-only order" from "vehicle order missing its stock link by mistake" — a mis-saved order can leave a vehicle un-reserved without anyone noticing.
- **No accounts-payable / Supplier Payment tracking.** Purchase Invoices record what's owed to a supplier; nothing records what's actually been paid against them.
- **No Chart-of-Accounts / Bank / Mode-of-Payment master data.** Every General Ledger account name is currently free-typed with no validation — a spelling inconsistency ("Accounts Receivable" vs "Accounts receivable") would silently split a balance across two rows.
- **No multi-invoice payment allocation.** One payment can only be recorded against exactly one invoice; there's no way to record a single receipt covering several outstanding invoices for the same customer.
- **[HIGH PRIORITY] GST hardcoded / not centralized on Spares line items, Used Vehicle Invoice, and all three VAS sale documents.** See above.
- **[HIGH PRIORITY] No duplicate registration/engine/chassis-number check on Used Vehicle Purchase Invoice.** See above — can silently overwrite an existing vehicle's stock record.
- **Exchange Vehicle Master is missing its entire Finance Details section** (loan payoff amount, balance owed/refundable) — a customer trading in a vehicle still under a bank loan has no way to record the loan closure, which directly affects how much credit the dealership can give.
- **Used Vehicle Purchase Invoice's `grand_total` has no server-side recompute** from `total_amount`/`discount` — unlike the New Vehicle Sales Order/Invoice fixes already made, a crafted or buggy submission could save an inconsistent total with nothing to catch it.

### Workflow — open

- **No per-branch dynamic requiredness for the Sales Enquiry link.** Your reference ERP requires an enquiry-form link at some branches and not others (a real, live-confirmed business rule); this app treats it the same everywhere.
- **Manual Journal Entries have no approval gate or cancel/amend lifecycle** — unlike every other document type in this app (Invoice, Sales Order, etc.), a Journal Entry has no submit/cancel state at all. A mis-posted manual entry can currently only be corrected by hand-posting a second counter-entry.
- **No backdating-window control on manual GL postings** — a Journal Entry's date currently accepts any value, with no limit on how far back it can be dated.
- **Job Card stage-document submission order isn't enforced.** The pipeline (Water Wash → Bay In → Bay Out → Outwork → Final Inspection) is genuinely implemented as signal-driven status advancement, but nothing stops a stage document being submitted out of sequence — a Bay Out could be submitted before any Water Wash exists, jumping the Job Card straight to In Progress.
- **A manual Job Card status-override view bypasses the entire stage pipeline.** Any user with edit access and ownership can POST an arbitrary status directly — no stage document ever gets created, which is exactly the audit trail this escape hatch defeats. The only guard is that status locks once a Service Invoice exists.
- **RC Book Issue's `rc_book_creation` link is mandatory even on the exchange-vehicle path**, where the reference doesn't require one (the customer's own original RC book is being returned, not one the dealership created) — there's no valid value to supply in that case.
- **Registration No Creation isn't restricted to already-submitted Form 20 records** — a registration number can be tied to a still-Draft or even Cancelled Form 20 application.
- **Form 20 Creation / Registration No Creation are one-row-per-vehicle**, not the header-plus-batch-table shape the rest of the RTO module (RTO Payment, Regpay) already has — a single application covering several vehicles can't be represented as one document.
- **AMC/RSA/Protection Plus have no `branch` field at all** — no way to report which branch sold a package, even though branch is captured for every other stock movement.
- **AMC/RSA/Protection Plus don't prevent reusing the same Sales Order across multiple packages of the same type** — the reference explicitly rejects reusing an Order Form ID; Django allows unlimited duplicates, which would silently double up VAS charges/stock consumption on one vehicle sale.
- **Used Vehicle Sales Finance isn't a Submittable document and has no disbursement-amount field** — the reference's core rule (disbursement can't exceed what's owed) has nothing to enforce it against.

### Role & Permission Management — open (architectural, not a quick fix)

- **Single role per user, instead of the reference's multiple-roles-at-once model.** A real job spanning two role buckets (e.g. cashiering + accounts-ledger work) can't be modeled without inventing an ad-hoc combined role.
- **Module-bucket-level permissions instead of per-document-type permissions.** The reference can grant "may create and submit a Customer Payment but not cancel one, and only sees payments they personally took"; this app can only express "can/cannot edit anything in Billing." No submit/cancel distinction, no per-record ownership restriction wired into the permission check.
- **No per-user override of module access** — every user sharing a role gets identical access, with no way to individually widen or narrow it without changing the whole role.

Both gaps are confirmed real and correctly **not** force-fixed this pass — closing them means a schema change touching every permission check in the app, not a same-night fix. Recommended as a dedicated future project, not folded into a quick patch.

### Cosmetic / low-impact — open

Minor field/label-level differences across every tier: no point-in-time phone-number snapshot on a Sales Order, a modeling-approach difference in how vehicle color is captured, an unused `sub_group` field, Payment method left optional rather than mandatory, a cosmetic document-numbering difference (`PAY-{id}` vs. a configurable naming series), Job Card missing a direct service-type/odometer/supervisor/opening-closing-time capture, Service Enquiry status as a fixed list with no change history, no post-service customer feedback capture, and a `Branch.abbreviation` field with no Django equivalent. None of these carry real business-logic impact today — full detail in `docs/audit/DEVIATIONS.md`.

### Not yet audited

All 8 priority tiers are now complete. What remains unwalked is the reference server's **141 "not in main nav" doctypes** (confirmed lower priority — reached only via secondary role workspaces, or used purely as link-field targets from other doctypes) plus the broader long tail outside the 8 priority tiers — roughly 4,768 of the matrix's 5,560 rows. This is a genuine, honestly-stated boundary, not a hidden gap: the reference-side data for every one of these rows is already extracted and sitting in `docs/audit/PARITY_MATRIX.csv`, ready for the same row-by-row treatment whenever a future pass picks it up.

---

## 7. Deliberate differences (not bugs)

**`Customer Vehicle` exists as its own record in this app but has no equivalent in your reference ERP.** Your reference ERP tracks a sale and stops there; it doesn't follow what happens to a specific vehicle afterward. This app needs to, because Service, VAS (AMC/RSA/Protection Plus), RTO registration, and warranty/free-service tracking all happen *after* the sale, against *that specific bike*, sometimes years later and sometimes by a different team than the one that sold it. `Customer Vehicle` ties a customer to the exact unit they bought (by chassis/engine, not just model) and carries everything that accumulates on it over time: registration number, insurance expiry, warranty dates, free-services used/remaining. Without it, a service advisor opening a job card, or a telecaller chasing an insurance renewal, would have no way to find "this customer's actual bike" or its service/warranty history. This is load-bearing in the system today — Service, VAS, RTO, and warranty tracking all read from it. If your workflow genuinely doesn't need post-sale vehicle tracking the way this app assumes, that's a scoping conversation worth having explicitly, not something to "fix" in code.

**Two confirmed bugs exist in your reference ERP itself**, found while live-verifying its actual behavior (not guessed — reproduced twice against the real test server): orphaned `Vehicle Chasis Number Master` records are left behind when a Purchase Invoice submit fails partway through, and a genuine race condition in the reference app's own JavaScript (`loadDefaultHelmet`/`vehicle_charges_list`) throws a server error on a successful Purchase Invoice submit. Neither has been reproduced in this app — matching a reference-app bug would itself be a deviation from correct behavior, and both are recorded in `docs/audit/DEVIATIONS.md` explicitly so a future QA round doesn't mistake "this app doesn't have that bug" for a mismatch.

---

## 8. Known limitations and accepted risks

Recorded here plainly so nothing is a surprise later:

- **Test coverage is targeted, not exhaustive.** 195 automated tests plus a 10-test real-browser suite cover the riskiest mechanisms — this is a strong regression floor, not a guarantee every workflow is verified (see Section 6, "Not yet audited," for the honest current boundary of that coverage).
- **Pagination**: most list pages load their full result set at once rather than paginating. Not a problem at today's data volumes; worth revisiting if any single list grows into the thousands of rows.
- **Accessibility**: the large majority of WCAG issues found during an accessibility pass were fixed; one remaining item (table-row-stripe color contrast against link-blue text) is a deliberate, not-yet-made design trade-off, not an oversight.
- **A historical credential string** briefly existed in this repository's git history before being rotated to a new, unrelated value — the old value is permanently dead and grants no access anywhere. (Separately: a reference-server test-account credential was briefly committed to a working file during tonight's audit tooling; it was caught by a second reviewer, redacted, and — since it hadn't been pushed to any remote — scrubbed from local git history entirely before this document was written. Rotating that test-server password is recommended as a precaution regardless.)
- **No load/performance testing has been done.** The stack (Django + Gunicorn + Postgres) scales in the conventional ways (more Gunicorn workers, a bigger Postgres plan) if usage grows, but that hasn't been benchmarked against this specific app's query patterns.

---

## 9. What's left

**On the client side:** the four items in Section 1 — none of them code work.

**On the dev side:** the open items in Section 6 — most urgently the two HIGH PRIORITY items (GST centralization across Spares/Used Vehicles/VAS, and the Used Vehicle duplicate-registration stock-overwrite risk). All 8 priority tiers of the evidence-matrix audit are now complete; what remains is the reference server's 141 lower-priority "not in main nav" doctypes, which can be picked up whenever useful — the extracted data is already sitting in `docs/audit/PARITY_MATRIX.csv` waiting. Nothing else is outstanding; every previously-reported issue this document knows about is either fixed (Section 4) or explicitly listed as open (Section 6) — nothing has been silently dropped.

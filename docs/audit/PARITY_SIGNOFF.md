# Parity Audit Sign-Off — 2026-07-20 → 2026-07-23 (all 8 tiers complete)

This replaces narrative-only status reports with an evidence-backed ledger. Every claim below traces to a file, a commit, or a row in `docs/audit/PARITY_MATRIX.csv` that you can open and check yourself — see "How to verify this yourself" at the bottom.

**This supersedes the 2026-07-20 partial sign-off** (which covered only Tiers 1-2 and explicitly flagged Tiers 3-8 as not-yet-walked). All 8 priority tiers are now complete.

## What was audited

1. **Freshness of the reference-server spec** (`reference_erp_spec/`: 429 custom doctypes, 201 client scripts on the client's live test server). Re-confirmed live against the running server — baseline current, no drift.
2. **Parity matrix scaffold**: all 429 custom doctypes' native fields, extracted from the reference server's own API, loaded into `docs/audit/PARITY_MATRIX.csv` (5,560 rows) as the row-by-row comparison ledger.
3. **All 8 priority tiers walked**, in business-impact order:
   - **Tier 1 — New Vehicle Sales Order chain** (Enquiry → Appointment → Order → Delivery → Invoice/GST)
   - **Tier 2 — Billing / Payments / GL**
   - **Tier 3 — Service / Job Card pipeline**
   - **Tier 4 — Spares** (parts inventory, purchase, counter sales, stock reconciliation)
   - **Tier 5 — RTO / Exchange** (registration, number plates, RC book chain, Exchange Vehicle)
   - **Tier 6 — Used Vehicles** (purchase → sale → delivery → invoice → RC hand-over pipeline)
   - **Tier 7 — VAS** (AMC / RSA / Protection Plus)
   - **Tier 8 — Masters / Admin / Roles** (Role & Permission Management fidelity)

## Matrix summary

| Status | Rows | What it means |
|---|---|---|
| Match | 402 | Confirmed same field/behavior, evidence-cited |
| Deviation | 85 | Field/behavior exists on both sides but differs |
| Missing | 277 | Reference has it, Django app doesn't |
| Fixed | 2 | Was a Deviation, closed this pass with a code fix (see below) |
| N/A | 24 | Layout-only rows (Section/Column Breaks — not real fields) |
| Deliberate-difference | 2 | Reference-app bugs, intentionally not reproduced |
| *(blank — not yet walked)* | 4,768 | Doctypes outside the 8 priority tiers — see "Explicitly not covered" below |

**792 of 5,560 rows (87 of 433 doctypes, ~20%) have been evidence-checked.** Every verdict was independently re-verified by a second reviewer against the actual source files before being accepted — no verdict shipped on a first pass alone. Two full reviewer catches this pass forced real corrections mid-audit: a false "drift" alarm in Task 1 (a wrong API filter, not real data loss — caught and fixed before it propagated) and 12 duplicate matrix rows accidentally created in Tier 7 (caught and removed with the report's inaccurate claims corrected).

## Bugs found and fixed across all 8 tiers

Six real, load-bearing bugs were found and fixed during the audit itself (separate from the 14-item client corrections-report plan run alongside this audit, which closed its own set of issues):

1. **`Invoice.cancel()` never reversed its auto-posted GL entry** (Tier 1) — a cancelled invoice permanently overstated Accounts Receivable and Sales Revenue. Fixed: posts a mirror-image reversing entry.
2. **Reconciling a Payment to Completed never posted its GL entry** (Tier 2) — only a payment *created* already-Completed did; the normal cash-collection workflow silently posted nothing. Fixed: both paths now post correctly.
3. **A Job Card could be invoiced immediately at `Pending` status** (Tier 3) — skipping the entire Water Wash → Bay → Final Inspection pipeline. Fixed: invoice creation now requires `service_status == READY`.
4. **Counter Sale Return could be submitted with no godown specified** (Tier 4) — the stock-restoration signal silently no-op'd, permanently losing the returned stock. Fixed: godown is now required at both the form and model layer.
5. **RC Hand Over (RTO) accepted a trade-in without the RC book or NOC in hand** (Tier 5) — a real legal-compliance gap; the reference's `before_save` gate existed but wasn't enforced in Django. Fixed: `rc_book_received='no'`/`noc='no'` are now rejected.
6. **RC Hand Over (Used Vehicles) had the identical unenforced gate** (Tier 6) — a separate doctype instance of bug #5, not a duplicate fix. Fixed the same way.

Every fix went through the same TDD + independent-reviewer cycle as the rest of this session's work, with test evidence traced by hand, not just "tests pass."

## Significant findings NOT fixed this pass (correctly deferred, not hidden)

Two findings are flagged as **high-priority candidates for the next dedicated fix pass**, ranked above the routine open-items list because of their blast radius:

- **GST hardcoded at a flat 9%/9%, uncentralized from `split_gst()`, no IGST handling — repeats across `spares/` (Tier 4), `used_vehicles.UsedVehicleInvoice` (Tier 6), and all three VAS sale docs (Tier 7).** This is the exact same class of bug already found and fixed once in `rto/` this session (commit `fdb3740`) — it just wasn't fixed everywhere it occurs. Four separate apps now need the same treatment.
- **Used Vehicle Purchase Invoice has no duplicate registration/engine/chassis-number check before creating stock** (Tier 6) — a re-submitted Purchase Invoice reusing an already-used registration number silently *overwrites* an existing vehicle's stock record, including force-resetting a Sold vehicle back to Available. This is a genuine data-loss path, independently confirmed during review, not just a missing-field gap.

Two architectural gaps were found in Tier 8 (Role & Permission Management) and correctly NOT force-fixed, since closing them requires a schema migration touching every permission check in the app:
- Single-role-per-user instead of the reference's many-to-many role assignment.
- Module-bucket-level permissions instead of the reference's per-DocType permission matrix (no submit/cancel distinction, no permission level, no per-record ownership restriction wired into the permission check).

The full ranked list — 24 open items across Financial/data-integrity, Workflow blockers, Role & Permission Management, and Cosmetic categories — is in `docs/audit/DEVIATIONS.md`, every one evidence-cited with exact file:line references.

## Deliberate differences (not bugs)

- **`Customer Vehicle` exists as its own record in this app but has no reference-server equivalent.** Explained in full in `PRODUCTION_DELIVERY_REPORT.md` — a scoping difference, not a gap to close.
- **Two confirmed bugs in the reference app itself** (orphaned `Vehicle Chasis Number Master` records on a failed Purchase Invoice submit; a race condition in the reference's own JavaScript on submit) — deliberately not reproduced, since matching a reference bug would itself be a deviation from correct behavior.
- **Tier 3's `Customer Call` vs. reference's `Follow Ups` doctype** — Django's implementation is a genuinely different, more useful call-log feature, not a port of the reference's click-to-dial settings singleton. Treated as a deliberate non-match, not scored as Missing.

## Explicitly not covered

**~4,768 of the matrix's 5,560 rows (346 of 433 doctypes) remain unwalked** — these are the reference server's 141 "not in main nav" doctypes (confirmed lower priority: reached only via secondary role workspaces or used purely as link-field targets) plus any doctype outside the 8 priority tiers' scope. This is the honest boundary of tonight's coverage, not a hidden gap: the reference-side field data for every one of these rows is already extracted and sitting in the CSV, ready for the same row-by-row treatment whenever a future pass picks them up.

## Regression status

Run fresh, directly, immediately before this sign-off:

- `python manage.py test` — **195/195 passing** (up from 151 at the partial Tier-1/2 sign-off, +44 tests added across Tiers 3-8's fixes and regression-coverage additions).
- `python manage.py test e2e` (Playwright, real browser) — **10/10 passing**.

No regressions across the full 8-tier audit's accumulated commits.

## How to verify this yourself

Open `docs/audit/PARITY_MATRIX.csv` and filter to `status != Match` and `status != ""` — every row's `evidence` column points to an exact `file:line` in this repo or a named test. Open `docs/audit/DEVIATIONS.md` for the same evidence in ranked, narrative form, including per-tier walkthrough summaries at the bottom explaining exactly what was checked and why each finding was or wasn't fixed. Every task went through a second independent reviewer who re-verified the cited evidence against the actual source files before the work was accepted.

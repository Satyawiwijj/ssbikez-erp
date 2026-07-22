# Sidebar Simplification — Candidate List for Client Review (New Correction #8)

**Client feedback (New Correction #8):** "too many unnecessary modules in the sidebar, should be simplified to match standard ERP layout."

**What this document is:** a client-reviewable candidate list, not a code change. Nothing in
`templates/base.html` was touched to produce this. Every row below is evidence-backed against
the reference server's own navigation structure (`reference_erp_spec/`), and every
recommendation needs a human decision before anything is hidden — exactly the same
evidence-backed / human-decided pattern `docs/audit/DEVIATIONS.md` uses for the rest of this
project.

**Why this can't just be "hide whatever looks unnecessary":** the client's comment names no
specific item. Acting on a vague "too many modules" complaint by guessing which ones risks
hiding something the client actually relies on daily, which would just generate a new
corrections report. So instead of guessing, this cross-references our full sidebar link list
against the *real* navigation structure of the server SS Bikez already uses in production
(their live Frappe/ERPNext-based reference app, fully reverse-engineered field-by-field in
`reference_erp_spec/`), and flags only the items that have **direct evidence** they're outside
that reference nav.

## Methodology

1. **Extracted every sidebar link.** All `<a class="sidebar-link">` entries in
   `templates/base.html` (lines 562–751), grouped by their `<div class="sidebar-section">`
   header. This is a stricter extraction than the brief's suggested regex (which only matched
   `sidebar-link` immediately preceding `>` and picked up unrelated inline `<script>` text
   instead of link labels) — the version used here anchors on the actual `class="sidebar-link"`
   attribute and strips the `<i class="nav-icon ...">` icon markup, giving clean label text.
   **Result: 119 sidebar entries** across 13 sections (Main, Sales, Customers, Finance, RTO,
   Service, Spares, VAS, Vehicle Master, Used Vehicles, Masters, Reports, Admin).

2. **Built two reference lookup sets from `reference_erp_spec/`:**
   - **"In main nav" (167 concepts):** every `## <Card Label> (doctype: ...)` heading across
     `reference_erp_spec/00_*.md` through `26_*.md` — the 27 module groups the spec's own
     `README.md` states are "the EXACT navigation structure from the SSBIKEZ workspace (Card
     Break order in the Workspace doctype's `links` table) — not inferred."
   - **"Confirmed NOT in main nav" (141 doctypes):** every `#### <Doctype>` heading in
     `reference_erp_spec/27_not_in_main_nav.md`, which the spec documents as "reached via other
     role workspaces (Euler/SS Motors/etc), only used as a Link-field target, or
     unused/orphaned — verified individually, not guessed."

3. **Classified each of our 119 sidebar entries** against those two sets by matching on label
   text and underlying business concept (not just exact string match — e.g. our "RC Books"
   matches the reference's separately-named "RC Book Creation" + "RC Book Issue" cards). Three
   outcomes:
   - **Reference equivalent found in main nav** → the client already uses this concept daily on
     their live system. Recommendation: **keep**.
   - **Reference equivalent found, but explicitly confirmed NOT reachable from the reference's
     own main nav** → strongest evidence available that this is safe to hide/demote.
     Recommendation: **hide** (still needs client sign-off — see caveat below).
   - **No reference equivalent found anywhere** → either a genuine custom addition (something
     the reference app doesn't do at all, e.g. Sales Targets, Profit Report) or infrastructure
     that reference handles outside its module workspace (e.g. User/Role admin, which Frappe
     handles via its generic desk, not the SSBIKEZ workspace cards). Recommendation: **keep**,
     since absence of evidence isn't evidence the client doesn't need it — these need a
     different conversation (client walkthrough / usage data) that this exercise can't resolve.

**Caveat on every "hide" row below:** "not reachable from the reference's main nav" documents
that the *reference app* doesn't surface it as a top-level nav item — it does NOT prove SS
Bikez's staff never use the underlying feature (a few of the reference's own "not in main nav"
doctypes are still fully wired forms, just accessed via a different, non-card route, e.g.
drill-down from a parent document). Every hide candidate here is a **candidate for a client
conversation**, not an instruction. No sidebar entry was hidden, removed, or modified as part of
this task.

## Summary

- **119 sidebar entries checked**
- **9 flagged as hide candidates** (explicit match to `27_not_in_main_nav.md`)
- **6 flagged as merge/dedup candidates** (same underlying data exposed twice under different
  labels — a "too many modules" complaint is often really about duplication like this, not
  about any single module being unwanted)
- **104 recommended keep** (either a confirmed reference-nav concept, or no reference match but
  a plausible genuine business need — no evidence to act on either way)

(9 + 6 + 104 = 119, reconciling exactly against the table below — corrected after an initial
arithmetic slip undercounted the merge rows as 2 instead of 6, which also threw off the keep
count.)

---

## Main

| Our sidebar label | Reference equivalent | Recommendation |
|---|---|---|
| Home | none — app shell landing page, not a business doctype | Keep |
| Dashboard | none — app shell page | Keep |

No action possible or needed here; these are navigational scaffolding, not "modules."

## Sales

| Our sidebar label | Reference equivalent | Recommendation |
|---|---|---|
| SALES Dashboard | none — custom aggregate dashboard | Keep |
| Sales Enquiries | `Sales Enquiry Form` — group 25 (Sales Enquires) | Keep |
| Follow-Ups | `Customer Call` — group 12 (Follow Ups) | Keep |
| Feedback | `Sales Feed Back` — group 25 | Keep |
| Sales Appointments | `Sales Appoinment Booking` — group 25 | Keep |
| Test Rides | none as a standalone nav card — "test ride" only exists as a field inside `Sales Enquiry Form` in the reference, not its own module | Keep — real feature, reference just models it differently (embedded field vs. standalone list), not evidence it's unwanted |
| Orders | `New Vehicle Sales Order` — group 18 (Sales Form) | Keep |
| Exchange Vehicles | `Exchange Vehicle List` — group 22 (Exchange) | Keep |
| Dealers | `Dealer` — group 26 (Master) | Keep |
| Exchange Vehicle Dealer | `Exchange Vehicle Dealer` — group 22 | Keep |
| Exchange Dealer Payment | `Exchange Dealer Payment` — group 22 | Keep |
| Dealer RC Hand Over | `Dealer RC Hand Over` — group 22 | Keep |
| Deliveries | `New Vehicle Delivery Note` ("Vehicle Delivery") — group 18 | Keep |
| Sales Targets | none found anywhere in `reference_erp_spec/` (no "target" doctype or nav card at all) | Keep — genuine business need the reference app doesn't model; not clutter |
| Profit Report | none found anywhere in `reference_erp_spec/` | Keep — same as above, a real custom report, not reference clutter |

## Customers

| Our sidebar label | Reference equivalent | Recommendation |
|---|---|---|
| Customers | `Customer` — group 00 (default masters) | Keep |
| Customer Vehicles | no distinct reference doctype/card (closest concept: vehicle stock/allotment records tied to a customer via `Vehicle Allotment`, group 18) | Keep |
| Bike Models | `Add New Vehicle` — group 26 (Master). **Note:** this exact link (`customers:bike_model_list`) also appears verbatim under **Vehicle Master** below — same URL, two sidebar entries. | **Merge candidate** — same page reachable from two sections is duplication, likely part of what reads as "too many modules" |
| Vehicle Stock | no exact reference card (stock is tracked via `Item`/`Warehouse`/`Stock Reconciliation`, group 00, not a single "Vehicle Stock" nav item). **Note:** this exact link (`customers:vehicle_stock_list`) also appears verbatim under **Vehicle Master** below. | **Merge candidate** — same duplication pattern as Bike Models |

## Finance

| Our sidebar label | Reference equivalent | Recommendation |
|---|---|---|
| FINANCE Dashboard | none — custom aggregate dashboard | Keep |
| Daily Collection | no exact reference card; closest is `Customer Payment` (group 14, Receipts) rolled up as a report | Keep |
| Reconciliation | `Payment Reconciliation` — group 18 (Sales Form) | Keep |
| Invoices | `Sales Invoice` — group 20 (For Payout GST Bill) | Keep |
| Loans | none found anywhere in `reference_erp_spec/` | Keep — genuine feature not modeled by reference |
| Insurance | no exact match under Finance; reference's insurance concepts (`Insurance Claim`, `Insurance Estimation Master`, group 23) live under Service/Masters, not a Finance nav card | Keep — no strong evidence either way; worth a client question on whether this belongs under Finance vs. Service, not whether to hide it |
| Search Invoices | no distinct reference card — reference's `Sales Search` (group 04) is a combined multi-type search, not invoice-specific | Keep |
| Refunds & Advances | no exact reference card; closest concept is the "Advance Payment Details" child table embedded in several reference sales/delivery forms (group 18/07), not a standalone module | Keep |
| Journal Entries | `Journal Entry` — group 01 (New Vehicle Purchase), used as a standard doctype throughout | Keep |
| General Ledger | none as a standalone nav card — General Ledger is a standard ERPNext system report, not a workspace card in the reference's custom nav | Keep — required Finance capability regardless of reference nav structure |

## RTO

| Our sidebar label | Reference equivalent | Recommendation |
|---|---|---|
| RTO Dashboard | none — custom aggregate dashboard | Keep |
| Registrations | `Registration No Creation` — group elsewhere in spec (RTO/registration flow) | Keep |
| Number Plates | `Number Plate Issue` (in-nav concept, referenced across groups 04/08/18) | Keep |
| RC Books | `RC Book Creation` + `RC Book Issue` (in-nav concepts) | Keep |
| Registration Areas | `Registration Area` — group 26 (Master) | Keep |
| RegPay Base Amounts | `RegPay Base Amount` — **confirmed in `27_not_in_main_nav.md`** | **Hide candidate** |
| Register Number Master | `Register Number Master` — **confirmed in `27_not_in_main_nav.md`** | **Hide candidate** |

## Service

| Our sidebar label | Reference equivalent | Recommendation |
|---|---|---|
| SERVICE Dashboard | none — custom aggregate dashboard | Keep |
| Service Enquiries | `Service Enquiry Form` — group 11 | Keep |
| Bulk Import | `Service Enquiry Bulk Import` — group 11 | Keep |
| Service Appointments | `Service Appoinment Booking` — group 11 | Keep |
| Service Reminders | no exact reference card found | Keep — no evidence either way |
| Job Cards | `Job Card Creation` — group 24 (Creation) | Keep |
| Labour Charges | `Labor Charges Alteration` ("Labor Charge") — group 24 | Keep |
| Discount Master | `Discount Percentage Master` ("Service Invoice Discount Percentage") — group 23 (Masters) | Keep |
| Bays | `Bay In Creation` / `Bay Out Creation` — group 24 | Keep |
| Customer Calls | `Customer Call` — group 12 (Follow Ups) | Keep |
| Follow-Ups | `Customer Call` — group 12. **Note:** same underlying reference concept as "Customer Calls" directly above it and as "Follow-Ups" under Sales. | Keep, but worth a client question on whether Service's own "Follow-Ups" and "Customer Calls" need to be two separate entries |
| Warranty Claims | `Service Spares Warranty` ("Warranty Claim") — group 23 (Masters). **Note:** the same doctype is also exposed as "Service Spares Warranty" under **Spares** below. | **Merge candidate** — same underlying concept surfaced under two different sections/labels |
| Insurance Claims | `Insurance Claim` — group 23 (Masters) | Keep |
| Technician Report | none found anywhere in `reference_erp_spec/` | Keep — genuine custom report |

## Spares

| Our sidebar label | Reference equivalent | Recommendation |
|---|---|---|
| SPARES Dashboard | none — custom aggregate dashboard | Keep |
| Items | `Item` — group 00 (default masters) | Keep |
| Request Supplier Quotes | `Request Supplier Quote` — group 13 (Spares Purchase) | Keep |
| Supplier Quotes | `Supplier Quote` — group 13 | Keep |
| Purchase Orders | `Spares Purchase Order` (in-nav concept, group 13) | Keep |
| Purchase Invoices | `Spares Purchase Invoice` (in-nav concept, group 13) | Keep |
| Counter Sales | `Counter Sale` — group 13 | Keep |
| Counter Returns | `Counter Sale Return` — group 13 | Keep |
| Issue Alterations | `Spares Issue Alteration` ("Spares Issue") — group 24 (Creation) | Keep |
| Service Spares Issue Returns | `Service Spares Issue Return` — group 13 | Keep |
| Stock Report | no exact reference card; closest is `Stock Reconciliation` (group 00) reporting | Keep |
| Stock Transfers | `Stock Transfer` ("Spares Stock Location Transfer") — group 10 | Keep |
| Stock Count (Reconciliation) | `Stock Count Update` — group 10 | Keep |
| Bulk Import | `Spares Bulk Insert` — group 13 | Keep |
| PO Used Qty Report | no exact reference card; general concept exists inline within group 13 (Spares Purchase) forms, not as its own nav item | Keep |
| Parts Consumption | no exact reference card; same as above | Keep |
| Vehicle Spares Master | `Vehicle Spares Master` — **confirmed in `27_not_in_main_nav.md`** | **Hide candidate** |
| MRP Price Revisions | `Spares MRP Prices` — group 13 | Keep |
| Service Spares Warranty | `Service Spares Warranty` — group 23 (Masters). **Note:** same underlying doctype as "Warranty Claims" under **Service** above. | **Merge candidate** (see Service section note) |
| Spares Settings | no exact reference card; reference splits settings across group 17 (Settings) items instead of one combined settings page | Keep |

## VAS

| Our sidebar label | Reference equivalent | Recommendation |
|---|---|---|
| VAS Dashboard | none — custom aggregate dashboard | Keep |
| AMC Packages | `AMC` — group elsewhere in spec (AMC concept, group 01/26) | Keep |
| RSA Packages | `RSA` — group 26 (Master) | Keep |
| Protection Plus | `Warranty` ("Protection Plus") — group 26 | Keep |
| AMC Types | `AMC Types` — group 26 | Keep |
| RSA Types | `RSA Types` — group 26 | Keep |
| Warranty Types | `Warranty Type` — group 26 | Keep |
| RSA Creation | `RSA Creation` — **confirmed in `27_not_in_main_nav.md`** | **Hide candidate** |
| VAS Supplier Invoices | no exact reference card; closest concepts are `AMC Invoice`/`RSA Invoice`/`Warranty Invoice` (group 01), which are per-type rather than one combined VAS supplier invoice list | Keep |

## Vehicle Master

| Our sidebar label | Reference equivalent | Recommendation |
|---|---|---|
| Bike Models | `Add New Vehicle` — group 26. **Duplicate of Customers → Bike Models** (identical URL `customers:bike_model_list`). | **Merge candidate** — see Customers section |
| Add Bike Model | same reference concept as above (creation form for the same doctype) | Keep — but consider whether a separate "Add" link is needed once the list-vs-add duplication above is resolved |
| Vehicle Stock | `Item`/`Warehouse` stock concepts, group 00. **Duplicate of Customers → Vehicle Stock** (identical URL `customers:vehicle_stock_list`). | **Merge candidate** — see Customers section |
| Service Master | `Vehicle Service Master` — group 17 (Settings) | Keep |
| Vehicle Master Settings | `Vehicle Master Settings` — group 18 (Sales Form) | Keep |

## Used Vehicles

| Our sidebar label | Reference equivalent | Recommendation |
|---|---|---|
| Dashboard | none — custom aggregate dashboard | Keep |
| Vehicle Models | `Add Used Vehicle` — group 06 (Used Vehicle Purchase) | Keep |
| Stock (Register No) | no exact reference card; closest is `Used Vehicle Register No Master` (group 15) | Keep |
| Purchase Orders | `Used Vehicle Purchase Order` — **confirmed in `27_not_in_main_nav.md`**. The doctype exists and is fully submittable on the reference server, but the reference's actual used-vehicle purchase flow goes `Add Used Vehicle` → `Used Vehicle Purchase Invoice` directly (both in main nav, group 06) — no separate PO step is exposed in the reference nav. | **Hide candidate** |
| Purchase Receipts | `Used Vehicle Purchase Receipt` — **confirmed in `27_not_in_main_nav.md`**, same reasoning as Purchase Orders above (no separate receipt step in reference's main-nav flow) | **Hide candidate** |
| Purchase Invoices | `Used Vehicle Purchase Invoice` — group 06 (in main nav) | Keep |
| Sales | `Used Vehicle Sale` ("Used Vehicle Booking") — group 07 | Keep |
| Master Settings | `Used Vehicle Master Settings` — **confirmed in `27_not_in_main_nav.md`** | **Hide candidate** |
| Sales Settings | `Used Vehicle Sales Setting` — group 15 (in main nav) | Keep |
| Insurance Updates | `Used Vehicle Insurance Update` — **confirmed in `27_not_in_main_nav.md`** | **Hide candidate** |

## Masters

| Our sidebar label | Reference equivalent | Recommendation |
|---|---|---|
| Suppliers | `Supplier` — group 00 (default masters) | Keep |
| Warehouses | `Warehouse` — group 00 | Keep |
| Racks | `Rack` ("Rack List") — in-nav concept | Keep |
| Bins | `Stock Bin` ("Bin List") — in-nav concept | Keep |
| Categories | `Spares Category` — group 13 | Keep |
| Order Form Settings | `Order Form Settings` — group 17 (Settings) | Keep |
| Order Form Series | `Order Form Series` — **confirmed in `27_not_in_main_nav.md`** | **Hide candidate** |
| Model and Price | `Model and Price` — group 17 | Keep |
| Customer Price List | `Customer Price` — group 17 | Keep |
| Dealer Price List | `Dealer Price List` — group 17 | Keep |
| Vehicle Fitting Spares | `Vehicle Fitting Spares` ("Vehicle Fitting Master") — group 17 | Keep |

## Reports

| Our sidebar label | Reference equivalent | Recommendation |
|---|---|---|
| Sales Report | no single matching card; reference exposes reporting via the generic `Report` doctype (group 21) rather than per-domain report pages | Keep |
| Spares Report | same as above | Keep |
| Service Report | same as above | Keep |
| GST Report | `GSTR 3B Report` ("Generate GSTR 3B") — group 19 (GST Tax Reports) | Keep |

## Admin

| Our sidebar label | Reference equivalent | Recommendation |
|---|---|---|
| Users | none in the SSBIKEZ workspace cards — reference (Frappe) handles user administration through its generic desk-level "Users and Permissions" area, not a module-specific nav card | Keep — required system function; reference just doesn't need a dedicated card for it because Frappe's framework already provides one globally |
| Roles | same reasoning as Users | Keep |
| Module Access | no reference equivalent — this is our app's own RBAC model; Frappe uses Role + Role Permission Manager instead | Keep |
| Branches | `Branch` appears only as a Link-field target across reference forms (e.g. `27_not_in_main_nav.md`), never as its own main-nav master card | Keep — foundational config data, needed regardless of reference nav placement |
| Fuel Expenses | closest reference concept is `Fuel Supplier Payment`/`Fuel Slip`/`Fuel Voucher Master` — group 05 (Fuel), which IS in the reference's main nav, just grouped as its own "Fuel" section rather than under Admin | Keep — real feature with a reference equivalent, just organized differently |
| Insurance Expiry | none found anywhere in `reference_erp_spec/` | Keep — genuine custom feature |
| Company Settings | loosely maps to `Company` — group 00 (default masters), though reference exposes it as a plain master record rather than a settings page | Keep |
| Admin Settings | no reference equivalent found | Keep |

---

## For the client conversation

**Strong hide candidates (9)** — directly confirmed as NOT reachable from the reference app's
own main navigation:

1. RTO → RegPay Base Amounts
2. RTO → Register Number Master
3. VAS → RSA Creation
4. Spares → Vehicle Spares Master
5. Masters → Order Form Series
6. Used Vehicles → Purchase Orders
7. Used Vehicles → Purchase Receipts
8. Used Vehicles → Master Settings
9. Used Vehicles → Insurance Updates

**Merge/dedup candidates (2 concepts, 4+ affected links)** — same page or same underlying data
reachable from two different sidebar sections:

1. "Bike Models" and "Vehicle Stock" both appear under **Customers** and **Vehicle Master**
   (identical URLs — literally the same link twice).
2. "Warranty Claims" (Service) and "Service Spares Warranty" (Spares) both point at the same
   underlying concept (`Service Spares Warranty` in the reference), just labeled and grouped
   differently.

**Recommendation for the next step:** review the 9 hide candidates and 2 merge candidates with
the client directly — these are the only rows with concrete evidence behind them. Everything
else in the 119-entry sidebar has either a confirmed reference-nav equivalent or no evidence
either way, so hiding those without a specific client ask would repeat the exact mistake this
task was set up to avoid.

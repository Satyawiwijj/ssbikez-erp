# Deviations Queue — 2026-07-20 Parity Audit

Ranked by business impact. Each item: status is one of Open / Fixed / Descoped.

Source: every row in `docs/audit/PARITY_MATRIX.csv` with `status` of `Deviation`
or `Missing`, as of Task 3's Tier 1 (New Vehicle Sales Order chain) walkthrough.
Related CSV rows that share one root cause are grouped into a single item below
so the queue reflects distinct fixes, not raw row count; every source row is
still named so it traces back to the matrix 1:1.

## Financial / data-integrity

- [ ] **Vehicle List.price_lists** — Missing: reference makes Price Lists mandatory on the vehicle stock record so a sale must be validated against an approved rate; Django's `CustomerPrice` master (`masters/models.py:311-321`) exists but is never referenced anywhere under `sales/` (confirmed by grep) — `VehicleSalesOrderForm.total_amount`/`booking_amount`/`discount_amount` (`sales/forms.py:186,205-207`) are free-typed decimal fields with only a help-text hint, no cross-check against a price list. This is a control gap on every single New Vehicle Sales Order, not an edge case — highest blast radius of the three items in this section. — Open
- [ ] **New Vehicle Sales Order.customer / gst_category** — Deviation: `VehicleSalesOrder.save()` (`sales/models.py:466-468`) only copies `customer.gst_category` onto the order `if not self.gst_category` — i.e. once set, it is never refreshed. `gst_category` is also a plain editable field on the form (`sales/forms.py:186`), so it can be hand-overridden and then never re-synced. If a user changes the linked customer on an existing order, the stale GST category silently persists, which drives the CGST+SGST vs IGST split — direct risk of an incorrectly taxed invoice with no error or warning. — Open
- [ ] **Vehicle List.vehicle_code (New Vehicle Sales Order.vehicle)** — Deviation: reference's Vehicle Code is a mandatory Link; Django's `VehicleSalesOrder.vehicle` FK is `null=True, blank=True` (`sales/models.py:363-368`), so a vehicle-sale order can be saved with no physical stock unit attached. `VehicleSalesOrderForm` help text (`sales/forms.py:178`) frames the blank case as intentional for spares/accessories-only orders, which narrows the real risk, but nothing distinguishes "spares order" from "vehicle order missing its stock link by mistake" at the model level — a mis-saved vehicle order can leave the matching `VehicleStock` row un-reserved/un-sold, undetected. — Open
- [x] **Invoice.cancel() doesn't reverse its auto-posted GL entry** — Deviation found and fixed during Task 5, not from the Tier 1 matrix walkthrough (not a `PARITY_MATRIX.csv` row): `Invoice.submit()` (`billing/models.py`) auto-posts a `JournalEntry` (Dr Accounts Receivable / Cr Sales Revenue) via `post_journal_entry`, but `Invoice.cancel()` previously only flipped `docstatus` (inherited from `DocStatusMixin.cancel`) and never reversed that entry — a cancelled invoice permanently overstated both accounts in the General Ledger. Also documented as an accepted risk in `CLIENT_GUIDE.md` §9/§6.7 prior to this fix. — Fixed: `Invoice.cancel()` now calls a new `reverse_journal_entry()` that posts a mirror-image `JournalEntry` (swapped debit/credit per line) tagged against the same invoice, guarded against double-reversal. See `billing/tests.py::InvoiceCancelReversesJournalEntryTests`.

## Workflow blockers

- [ ] **New Vehicle Sales Order.sales_enquiry_form + Branch.allow_without_enquiry_form** — Missing: the reference app gates whether the enquiry-form link is mandatory per branch, live-verified as required at Coimbatore/Sulur-E/Tiruppur and not required at Gobi/Nambiyur/Puliampatti/Sathyamangalam/Sulur/Trichy. Django has no `allow_without_enquiry_form` field on `accounts.Branch` (`accounts/models.py:93-106`) and `VehicleSalesOrder.enquiry` is unconditionally optional for every branch (`sales/models.py:352-357`), with no branch-conditional requiredness logic in `sales/forms.py`. The branch-specific enquiry-tracking step of the sales workflow is currently unenforceable anywhere in the app. — Open

## Cosmetic / low-impact

- [ ] **New Vehicle Sales Order.phone_number** — Missing: no `phone_number` field on `VehicleSalesOrder` (`sales/models.py:352-464`). The phone number is still available live via the linked `customers.Customer.phone` (`customers/models.py:23`); this only means the order doesn't keep its own point-in-time snapshot if the customer's phone is later edited. — Open
- [ ] **Vehicle List.vehicle_color** — Deviation: reference derives color from a Customer Price/price-list selection; Django models `color` as a direct field on the physical stock unit (`customers/models.py:100`). Functionally equivalent for recording the vehicle's color — this is a modeling-approach difference, not a missing capability. — Open
- [ ] **Vehicle List.sub_group** — Missing: no `sub_group` field on `customers.VehicleStock` (`customers/models.py:81-106`), though `masters.CustomerPrice.sub_group` exists for price-list grouping. Since `CustomerPrice` isn't wired into the sales flow at all yet (see the `price_lists` item above), this has no live business-logic impact today. — Open

## Reference-app bugs, deliberately not reproduced

- [x] Orphaned Vehicle Chasis Number Master records on failed Purchase Invoice submit — Deliberate-difference: reference app bug, not reproduced by design — replicating it would itself be a deviation from correct behavior. See `reference_erp_spec/31_LIVE_VERIFIED_flows.md` §1.
- [x] loadDefaultHelmet/vehicle_charges_list race condition on Purchase Invoice submit — Deliberate-difference: reference app bug, not reproduced by design. See `reference_erp_spec/31_LIVE_VERIFIED_flows.md` §1.

## Not covered this pass

- [ ] Tiers 2-8 (Billing/GL, Service, Spares, RTO/Exchange, Used Vehicles, VAS, Masters/Admin) — Descoped-tonight: only Tier 1 (New Vehicle Sales Order chain) has been walked so far (Task 3). The remaining ~5,537 blank rows of the matrix's 5,549 total (everything outside Tier 1) haven't been evidence-checked yet — that's Task 7, later tonight. This is a sequencing gap, not a permanent scope cut.

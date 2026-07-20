# Deviations Queue — 2026-07-20 Parity Audit

(Sections below are filled in by Task 4; this file is created early by Task 3
because the "reference-app bugs" section below is established during the
Tier 1 walkthrough, not derived from the parity matrix.)

## Reference-app bugs, deliberately not reproduced

- [x] Orphaned Vehicle Chasis Number Master records on failed Purchase Invoice submit — Deliberate-difference: reference app bug, not reproduced by design — replicating it would itself be a deviation from correct behavior. See `reference_erp_spec/31_LIVE_VERIFIED_flows.md` §1.
- [x] loadDefaultHelmet/vehicle_charges_list race condition on Purchase Invoice submit — Deliberate-difference: reference app bug, not reproduced by design. See `reference_erp_spec/31_LIVE_VERIFIED_flows.md` §1.

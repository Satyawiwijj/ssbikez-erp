# Reference Server Freshness Check

**Date:** 2026-07-20  
**Script:** `reference_erp_spec/tools/refresh_check.py`  
**Status:** ✓ Baseline Confirmed (After Fix)

---

## Corrected Execution Result

```
Live doctype count (Ssbikez module): 429 (baseline: 429)
Live client script count: 201 (baseline: 201)
Baseline confirmed current.
```

**Exit Code:** 0 (no drift)

---

## False Alarm Explanation

### Initial Report (2026-07-20, Run 1)

An earlier run of this script incorrectly reported **99.5% data loss** (2 vs 429 doctypes), flagging the reference server's data as critically corrupted. This was a **false alarm caused by an incorrect filter in the Frappe API query**.

**Root Cause:** The script's DocType query included `["custom","=",1]` in its filter. In Frappe/ERPNext, the `custom` field (a boolean: 0/1) flags doctypes created ad-hoc through the Customize-Form or New-DocType UI. Doctypes that ship as part of an installed custom app's module (like all of Ssbikez's doctypes) are **not** flagged `custom=1` even though they belong to a custom module — they are regular app doctypes with `custom=0`.

By filtering `module="Ssbikez" AND custom=1`, the query matched only hand-crafted customizations (2 records), not the module's core doctypes (427 records). The filter was simply the wrong condition; it was never a real signal for "belongs to the Ssbikez module."

### Corrected Run (2026-07-20, Run 2)

The filter was corrected to `module="Ssbikez"` (removed the `custom=1` clause). The corrected query now returns **429 records**, exactly matching the baseline.

**Conclusion:** The reference server has NOT lost data. The 429/201 baseline is confirmed current and trustworthy for all downstream parity comparison tasks.

---

## Analysis

### Doctype Count

**Status:** ✓ Baseline Confirmed

The live doctype count matches the baseline exactly: **429 doctypes** in the Ssbikez module. All spec files in `reference_erp_spec/` are current and reliable for parity comparison.

### Client Script Count

**Status:** ✓ Baseline Confirmed

The live client script count matches the baseline exactly: **201 scripts**. This portion of the spec remains current and can be trusted.

---

## Notes

- The reference server is reachable and authentication succeeded
- Network calls completed without timeout or connection errors
- The earlier false-alarm run has been documented for transparency — this demonstrates the importance of validating filter logic in API queries
- Frappe `custom` field semantics: flags user-created customizations, not app module membership
- No data loss; no server issues; baseline is confirmed trustworthy

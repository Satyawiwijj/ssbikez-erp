# Reference Server Freshness Check

**Date:** 2026-07-20
**Script:** `reference_erp_spec/tools/refresh_check.py`

## Execution Result

```
Live custom doctype count (Ssbikez module): 2 (baseline: 429)
Live client script count: 201 (baseline: 201)
DRIFT DETECTED — re-pull affected spec files before trusting them.
```

**Exit Code:** 1 (drift detected)

## Analysis

### Doctype Count Drift

**Status:** ⚠️ CRITICAL DRIFT DETECTED

The live reference server reports only **2 custom doctypes** in the Ssbikez module, whereas the baseline spec recorded **429**. This represents a severe reduction (≈99.5% loss).

**Impact:** All spec files in `reference_erp_spec/` that document Ssbikez custom doctypes are now **unreliable** and must be re-pulled before any parity comparison tasks use them.

**Files Affected:** 
- Any `reference_erp_spec/*_*.md` file containing DocType specifications
- Requires manual re-pull of the complete DocType manifest before Tasks 2-8 can proceed with doctype comparisons

### Client Script Count

**Status:** ✓ Baseline Confirmed

The live client script count matches the baseline exactly: **201 scripts**. This portion of the spec remains current and can be trusted.

## Recommended Action

Before proceeding with Task 2 or later parity comparison tasks:

1. **Do NOT trust DocType specs** — they are outdated as of this check
2. **Re-pull the DocType manifest** from the reference server with current production credentials
3. **Verify the new count** to understand why the reference server now has only 2 custom doctypes
4. **Update the baseline** in this document and `reference_erp_spec/README.md` once the reason is understood
5. **Proceed with parity tasks** only after the spec has been refreshed

## Notes

- The reference server is reachable and authentication succeeded
- Network calls completed without timeout or connection errors
- The drift appears to be genuine (not a credential issue or API filter mismatch)
- Client scripts are stable — focus on diagnosing the doctype loss

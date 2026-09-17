# EVIDENCE REMEDIATION — CAP-DR-01 & CAP-INTG-07

**Date:** 2026-09-18  
**Authority:** Matt OWNER AUDIT DECISIONS 2026-09-18  
**Action this mission:** Document gaps only. Do **not** attempt the proofs here.

Both caps remain **SPECIFIED** (credits v1.0: 0.05). Overnight PROVEN proposals were rejected.

---

## CAP-DR-01 — still missing for PROVEN

Historical evidence retained (not deleted):

- B2 restore drill 2026-08-29 (sha256 match) bound under deliveries
- `restore-drill.py` / wrapper existence
- backup_status snapshot citations

**Still required for PROVEN (not done in this mission):**

1. A **deterministic canonical restore-drill proof** bound to CAP-DR-01 under beta-os (repeatable script/test path, not only a dated narrative report).
2. Clear provenance that the proof exercises the approved restore path without Production mutation.
3. Fresh CAP-bound Beta drill log under `docs/deliveries/` when READY is later sought (separate from PROVEN).

Until (1)–(2) exist, maturity stays SPECIFIED.

---

## CAP-INTG-07 — still missing for PROVEN

Historical / repo evidence retained (not deleted):

- `.env.example` template without live secrets
- `.gitignore` env/secret globs + sacred Beta/Production rule
- `scripts/tests/test_cap_intg_07_environment_separation.py` (renamed so `*secret*` gitignore does not hide it)

**Still required for PROVEN (not done in this mission):**

1. Deterministic proof beyond static repo checks — e.g. vault/rotation/separation behaviour appropriate to the CAP, not only gitignore + example-env presence.
2. Evidence that Production secret store separation is verified at the CAP boundary (without this mission performing Production or external-write work).

Until those proofs exist, maturity stays SPECIFIED. Repo checks remain evidence of SPECIFIED/config hygiene only.

---

CLAIMED ≠ VERIFIED · BUILT ≠ PROVEN · READY ≠ HUMAN COMMISSIONED

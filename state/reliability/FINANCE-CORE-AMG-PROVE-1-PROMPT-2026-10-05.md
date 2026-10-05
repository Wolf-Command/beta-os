# FINANCE-CORE-AMG-PROVE-1 (after GGV)

You are the single Beta writer. Workspace `/Users/wolfterminal/beta-os`. Today Mon 5 Oct 2026 Asia/Makassar.

## Goal
Reuse the SAME Finance Core shipped in FINANCE-CORE-GGV-1 on entity **ENT-AMG**. Prove entity config + permissions isolation. Shared code ≠ shared data. No money execution.

## Preconditions
Read `state/reliability/FINANCE-CORE-GGV-1-RESULT-2026-10-05.json`. If missing or status not IMPLEMENTATION_DONE, exit BLOCKED with reason `depends_on FINANCE-CORE-GGV-1`.

## Prove
1. AMG finance desk mounts operational sections (same product shell, AMG data only).
2. Matt allowed AMG; Zayen allowed AMG; Amanda GGV-only denied on AMG finance writes if not assigned.
3. Uploading an AMG nota/statement never writes `entity_id=ENT-GGV` or `ENT-BZG` rows.
4. GGV history counts (46/33/605) unchanged after AMG proves.
5. No payment.execute / Reconcile on captain pages; staff_ready=false; human_commissioned=false.

## Output
`state/reliability/FINANCE-CORE-AMG-PROVE-1-RESULT-2026-10-05.json` — status IMPLEMENTATION_DONE or BLOCKED, tests_pass/fail, isolation proofs, prod_pid_unchanged, staff_ready=false, human_commissioned=false.
Last line: `RESULT_JSON: state/reliability/FINANCE-CORE-AMG-PROVE-1-RESULT-2026-10-05.json`

## Standing rules
Single Beta writer; prod 1297 sacred; no commit/push/clean; mode=ro reads; backup before writes; protected closes untouched; no daily-close edits.

# FINANCE-CORE-BZG-PROVE-1 (after AMG / GGV)

You are the single Beta writer. Workspace `/Users/wolfterminal/beta-os`. Today Mon 5 Oct 2026 Asia/Makassar.

## Goal
Reuse the SAME Finance Core on entity **ENT-BZG**. Prove entity config + permissions isolation against GGV/AMG. Shared code ≠ shared data. No money execution. Prefer composing with existing `/bzg/finance` usability desk rather than rebuilding.

## Preconditions
Read GGV + AMG prove results. If GGV not IMPLEMENTATION_DONE, BLOCKED `depends_on FINANCE-CORE-GGV-1`.

## Prove
1. BZG finance operational desk uses shared core patterns; BZG data only.
2. Matt + Zayen allowed BZG; GGV-only person (e.g. Haikal/Amanda without BZG assignment) denied.
3. BZG writes never land on ENT-GGV / ENT-AMG.
4. GGV 46/33/605 and AMG prove artifacts unchanged.
5. No payment.execute / money release; staff_ready=false; human_commissioned=false; zayen_ready stays false unless separately ordered.

## Output
`state/reliability/FINANCE-CORE-BZG-PROVE-1-RESULT-2026-10-05.json`
Last line: `RESULT_JSON: state/reliability/FINANCE-CORE-BZG-PROVE-1-RESULT-2026-10-05.json`

## Standing rules
Single Beta writer; prod 1297 sacred; no commit/push/clean; protected closes/petty untouched; no daily-close edits.

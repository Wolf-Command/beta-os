# Cursor brief — BF-content-engine-haikal-upload-14fail-20261001

P0 human commissioning FAIL repair. Credit exception: `human_commissioning_fail_repair_P0`.

## Read and execute
1. `docs/deliveries/SPEC-Content-Engine-Haikal-Upload-14Fail-2026-10-01.md`
2. `docs/RULE-Content-Engine-Haikal-Upload-14Fail-2026-10-01.md`
3. FAIL JSON: `state/final-completion/beta-house-20261001/CONTENT-ENGINE-HAIKAL-UPLOAD-14FAIL-20261001.json`

## Live tree (Mac Studio)
- Workdir: `/Users/wolfterminal/beta-os` · branch `build/wolf-command-rebuild` · soft head `b3739a7` (preserve uncommitted sibling work)
- Serve: `scripts/serve_beta.py` pid **12379** · port **8788** · log `/tmp/serve_beta.log`
- Key code: `scripts/smart_upload.py`, upload routes in `serve_beta.py`, Content UI content-2.0
- Prod `:8787` READ-ONLY sacred — never touch

## Incident
Haikal: 14× `.MOV`, brand Tropik, detail `bbq-night-grill`. preview-names OK. UI **14/14 failed**. Investigate **shared path first**. Do not guess root cause from screenshot. HTTP 200 on `/api/upload/smart` ≠ success — check JSON body / `ui_status`.

## Must (SOFTWARE-FIRST)
SPEC → data (DB/NAS/temp) → perms → rules → API → UI → tests. Prefer shared upload/NAS/DB roots; reuse Wolf Core.

1. Extract actual exception from `/tmp/serve_beta.log` for this batch window.
2. Trace one failed file E2E (auth→limits→endpoint→temp→validation→NAS→DB→UI).
3. Check regression from recent NAS/content-stack Beta House changes.
4. Preserve failed batch; never mark those 14 successful manually; no duplicate assets on retry.
5. UX: human-useful errors + Retry; tech detail in admin logs only.
6. Eng prove E1–E8 on deployed Beta (single + multi MOV, naming, tropik brand, NAS dest/checksum, DB once/no dup retry, partial-batch safe, UI).
7. Deploy **Beta only**. Evidence under `state/build-factory/` + `state/final-completion/beta-house-20261001/` (+ optional commissioning evidence JSON).
8. STOP for Peaches verify + Haikal retest. **No staff_ready. No Exit Report. No Wolf Intelligence. Do not invent LIVE.**

## Out
Prod mutate · ask Haikal/Matt to diagnose · redesign Plan/ZIP/unrelated shell · tip-checkout finance/ops lanes · new agents

## Done when
E1–E8 proven on :8788, commit + tests, EXIT summary printed, stopped for Peaches/Haikal. `staff_ready` remains false.

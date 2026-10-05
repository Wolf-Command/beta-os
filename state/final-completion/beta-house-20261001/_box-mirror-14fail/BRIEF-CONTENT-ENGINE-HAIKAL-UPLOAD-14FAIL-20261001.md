# BF-content-engine-haikal-upload-14fail-20261001

P0 human commissioning FAIL repair. Credit exception: human_commissioning_fail_repair_P0.

## Live tree (Mac Studio)
- Workdir: `/Users/wolfterminal/beta-os`
- Serve: `scripts/serve_beta.py` pid **12379** · port **8788**
- Log: `/tmp/serve_beta.log`
- Key: `scripts/smart_upload.py`, upload routes in `serve_beta.py`, Content UI content-2.0
- Prod `:8787` READ-ONLY sacred — never touch

## Incident
Haikal: 14 `.MOV`, brand Tropik, detail `bbq-night-grill`. preview-names OK. UI 14/14 failed. Investigate shared path first.

## Must
1. Find actual exception in `/tmp/serve_beta.log`. Do not guess from screenshot.
2. Trace one failed file E2E (auth→limits→endpoint→temp→validation→NAS→DB→UI).
3. Check regression from recent NAS/content-stack Beta House changes.
4. Preserve failed batch; never mark those 14 successful manually; no duplicate assets.
5. UX: human-useful errors + Retry; tech detail in admin logs only.
6. Eng prove: single MOV, multi batch, naming, brand, NAS dest, checksum, DB once, no dup retry, partial-batch safe, UI.
7. Deploy **Beta only**. Evidence under `state/build-factory/` + `state/final-completion/beta-house-20261001/`.
8. STOP for Peaches verify + Haikal retest. No staff_ready. No Exit Report. No Wolf Intelligence.

FAIL: `state/final-completion/beta-house-20261001/CONTENT-ENGINE-HAIKAL-UPLOAD-14FAIL-20261001.json`

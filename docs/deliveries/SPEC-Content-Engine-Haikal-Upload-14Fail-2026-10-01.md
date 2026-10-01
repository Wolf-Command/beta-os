# SPEC — Content Engine Haikal Upload 14/14 FAIL Repair (1 Oct 2026)

**Run:** `BF-content-engine-haikal-upload-14fail-20261001`
**Owner order:** Matthew via Peaches P0 ~12:58 WITA 1 Oct 2026
**Class:** Human commissioning FAIL repair · credit exception `human_commissioning_fail_repair_P0`
**Workspace:** `/Users/wolfterminal/beta-os` · branch `build/wolf-command-rebuild` · soft head `b3739a7` (do not destroy uncommitted sibling work)
**Live Beta:** `scripts/serve_beta.py` pid **12379** · port **8788** · log `/tmp/serve_beta.log`
**Prod:** `:8787` READ-ONLY SACRED (do not touch)
**RULE:** `docs/RULE-Content-Engine-Haikal-Upload-14Fail-2026-10-01.md`
**FAIL record:** `state/final-completion/beta-house-20261001/CONTENT-ENGINE-HAIKAL-UPLOAD-14FAIL-20261001.json`
**Commissioning:** `state/commissioning/CONTENT-ENGINE-HAIKAL-UPLOAD-14FAIL-20261001.md`
**GATE:** `state/build-factory/GATE-content-engine-haikal-upload-14fail-20261001.json`
**Paste brief:** `briefs/cursor/BF-content-engine-haikal-upload-14fail-20261001.md`
**staff_ready:** false until Haikal retest PASS

## Incident (facts only — do not invent root cause)
- Actor: Haikal · brand **Tropik** · detail `bbq-night-grill` · **14× .MOV** · UI **14 failed of 14**
- UI: “Stopped — 14 failed of 14. Nothing was marked complete…”
- Naming / `POST /api/upload/preview-names` reached (deterministic names generated for all 14)
- Access-log note for Cursor: `POST /api/upload/smart` may return **HTTP 200** while body is `ok: false` / `ui_status` failed — **HTTP status alone is not success**
- Historical log leads (extract real exceptions; may or may not be this batch): `sqlite3.OperationalError: unable to open database file`; historical `POST /api/upload/smart` **403**; `BrokenPipeError`; SyntaxError / port-busy noise elsewhere in the same log file
- Shared infrastructure / path first (all 14 failed together)

## Goal
Restore reliable Smart Upload on **deployed Beta :8788** for Haikal-shaped sessions so a Tropik video batch (and general MOV upload) reaches NAS + index + Library with human-useful failures and safe Retry — without touching Prod.

## SOFTWARE-FIRST order (mandatory)
1. **SPEC** — this file + RULE (locked)
2. **Data** — DB paths, NAS dest roots, temp/staging dirs, checksum/hash evidence, index rows; verify openable/writable under the live Beta process user
3. **Perms** — auth / brand scope / assignment for Tropik under Haikal identity; forbid silent 403/empty error
4. **Rules** — upload lifecycle COMPLETE = NAS file + index + Library-retrievable; no manual success marking; no dup on retry
5. **API** — `preview-names` + `/api/upload/smart` (+ related NAS/status/recent); honest `ok`/`error`/`ui_status` bodies
6. **UI** — content-2.0 upload: human-useful error + Retry; tech detail in admin logs only
7. **Tests** — extend or add content-engine upload tests; FAIL=0 on touched suite; eng prove gates below

Prefer shared roots (`scripts/smart_upload.py`, serve_beta upload routes, NAS/DB helpers, brand/ACL providers) over one-off page patches. Reuse Wolf Core; no tip-checkout of unrelated finance/ops lanes.

## Investigation (Cursor owns — do not ask humans)
1. From `/tmp/serve_beta.log`, extract the **actual exception / response body** for the Haikal Tropik batch window (~12:58 WITA 1 Oct). Prefer request correlation over screenshot guess.
2. Trace **one** failed .MOV E2E under Haikal-sim on :8788:  
   auth → limits → preview-names → smart → temp/stage → validation → NAS copy/verify → DB/index → UI status.
3. Check regression from recent Beta House NAS/content-stack changes on this branch (do not revert unrelated uncommitted work).
4. Confirm whether failures are shared (path/DB/NAS/auth) vs per-file; fix the shared root first.

## Repair scope
- Fix the shared failure so single + multi MOV upload PASS on Beta for authorised brands (Tropik required).
- Preserve failed batch provenance; never mark those 14 successful by hand; retries must not duplicate NAS assets.
- UX: human-useful per-item + batch error + Retry where safe; stack traces only in server/admin logs.
- Partial-batch safe: successes stay; failures retryable independently.
- Deploy / restart **Beta serve only** if required. Prod :8787 process and tree untouched.

## Out of scope
- Prod :8787 mutate · invent LIVE · staff_ready=true · Exit Report · Wolf Intelligence delivery · asking Haikal/Matt to diagnose · redesign Content Plan / ZIP / unrelated shell · finance/ops tip-checkouts · new agents/dashboards

## Engineering prove (Beta :8788) — all required
E1 single MOV upload PASS  
E2 multi-video batch PASS (≥3)  
E3 generated naming correct  
E4 brand association **tropik** correct  
E5 NAS destination correct; file exists; size/checksum sane  
E6 DB/index record **once**; retry does not duplicate  
E7 partial-batch failure safe; failed item retryable  
E8 desktop UI human-useful error + Retry  

Evidence under:
- `state/build-factory/` (this run)
- `state/final-completion/beta-house-20261001/`
- optional gate JSON: `state/commissioning/evidence/CE-HAIKAL-UPLOAD-14FAIL-GATE-2026-10-01.json`

## Human retest (after Peaches light verify — not Cursor)
Haikal small real batch → then normal batch. Upload completes; files on intended storage; Library sees them; names+brand correct; Haikal can find/preview/use. **staff_ready stays false until that PASS.**

## Deliver / EXIT
- Commit(s) on Beta branch with tests; do not destroy soft-head sibling dirty work.
- Print EXIT with E1–E8 PASS/FAIL, commit hash, test counts, honest gaps.
- STOP for Peaches verify + Haikal retest. Do not claim staff_ready or LIVE.

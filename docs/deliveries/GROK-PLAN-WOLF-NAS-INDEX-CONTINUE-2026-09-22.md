# GROK PLAN — Wolf NAS read-only index continue — 2026-09-22

**Run:** BF-wolf-nas-index-continue-20260922
**Prior:** NAS Library Upload P0 ENGINEERING PASS=60 (staff_ready=false). Brand-Assets + _Imports samples only.
**Bound:** Beta :8788 only. Production :8787 sacred — no mutate.
**Authority:** RULE-Wolf-Connection-Commissioning-NAS-GoLive-2026-09-22.md + WOLF-NAS-SOURCE-REGISTRY-2026-09-22.md.
**PRIORITY-QUEUE:** wolf-nas-index-continue-20260922 P0.

## Goal
Continue NAS DISCOVER → INVENTORY → HASH → INDEX (read-only). Widen sample index beyond Brand-Assets/_Imports into more top folders under /Volumes/01-Media-Library without mutating NAS files and without inventing staff go-live or Haikal PASS.

## In scope
1. Extend `scripts/core/nas_library.py` sample/index path to additional safe top folders (AMG, AMG-Atrium, BZG, GGV, Clients, _Shared) with per-folder caps — READ-only walk + optional partial hash; never rename/move/delete/overwrite NAS.
2. Persist under `state/nas-index/` + Beta `nas_index` table (additive). Update registry indexing-state honesty.
3. Keep `/api/nas/registry`, `/api/nas/index/sample`, `/api/nas/index/search` working; add folder filter if missing; no `/Volumes/` path leak to clients.
4. Content Engine / library search can surface newly indexed assets for authorised scopes only (wrong-scope 403).
5. Tests: unit + live Beta prove. Honesty proven=false ready=false staff_ready=false. ClickUp+Telegram stay RETIRED.
6. `:8787` pid untouched.

## Out of scope
- Haikal human upload/search/preview/download (Needs Staff — morning)
- Full 40k tree hash in one shot (background incremental OK; do not claim complete)
- B2 restore; Production deploy; destroy/reorg NAS
- FIN/HR/Trading; invent PROVEN/READY/staff_ready; Metricool publish; Email send
- Cloudflare seats (Owner-only)

## Success / EXIT
- Suite PASS FAIL=0
- At least 2 additional top folders sampled into nas-index (beyond Brand-Assets/_Imports) with evidence counts
- Registry + GROK-REVIEW honesty updated; staff_ready remains false
- Production untouched

## Cursor rules
- ASCII prompts only; short pointer prompt to this plan
- Do NOT destroy NAS. Additive Beta state only.
- Prefer Shell-tracked short cursor-agent launch

EXIT: SUCCESS with PASS=/FAIL=0 and GROK-REVIEW-WOLF-NAS-INDEX-CONTINUE-2026-09-22.md written.

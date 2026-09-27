# GROK REVIEW — AKR live prove c4ba95a

**Commit:** `c4ba95a` feat(intel): prove Habitat authorised knowledge on live sources
**Date:** 2026-09-18 (factory watch INSPECT→ADVANCE → GROK_REVIEW)
**Bound:** akr-live-prove-v1
**Verdict:** **PASS**

## Diff vs mission

| Requirement | Present in c4ba95a | Result |
| --- | --- | --- |
| Extend authorised_knowledge.py (not replace) | pipeline + live retrieve added; resolve() kept | PASS |
| New akr_habitat_live_registry.json | 4 explicit sources + 3 allowlisted roots | PASS |
| Live tests test_authorised_knowledge_live.py | font/voice/conflict/empty/absent + security | PASS |
| No CRM / lead spine / Klaviyo / staff grants | name-status clean of those paths | PASS |
| Do not edit phase26_team / migrate / skills / wolf_intelligence | not in commit (dirty WIP stays unstaged) | PASS |
| PDF via /opt/homebrew/bin/pdftotext + page + sha256 | PDFTOTEXT_BIN + provenance page/sha256 | PASS |
| brand_font Manrope CLIENT_APPROVED when PDF read | live.font.* PASS | PASS |
| ui_font Inter ui_chrome; not CONFLICTED with brand | live.font.ui_inter + lanes_not_conflicted | PASS |
| brand_voice EVIDENCE passage; no interpretation field | live.voice.* PASS | PASS |
| headline_case CONFLICTED; no winner; peer OPERATIONAL | live.conflict.* PASS | PASS |
| Empty canonical → NOT CANONICAL not UNKNOWN | live.empty.* PASS | PASS |
| Absent key → NOT FOUND/UNKNOWN + attempt_log | live.absent.* PASS | PASS |
| Security: .. / wrong scope / bytes / png | sec.* PASS | PASS |
| Fixture tests still pass | test_authorised_knowledge.py PASS=51 | PASS |
| One commit; message matches | c4ba95a only on range | PASS |

## Soft note (not FAIL)

1. Mission doc committed under `docs/deliveries/CURSOR-MISSION-AKR-LIVE-PROVE-2026-09-18.md` — content-only, matches authorised brief.
2. Extractors are Habitat-literal (Manrope / Inter / lowercase-only). Acceptable for this explicit-source live prove; not a general NLP layer.
3. Cursor log had a trailing bare `EXIT:` after `EXIT:0`, which made `bf_watch` reverse-scan return null (INSPECT). Watch recovered by stripping the empty line and appending `CURSOR_DONE` / `EXIT:0`, then `bf_advance` → GROK_REVIEW. Factory log writers should not emit empty `EXIT:`.

## Red team

| Attack | Result |
| --- | --- |
| Path `..` outside allowlist | PASS — INACCESSIBLE |
| brand:uma-blu source on brand:habitat ask | PASS — not retrieved |
| Unsupported .png type | PASS — INACCESSIBLE |
| Oversized source body in logs | PASS — capped; no full dump |
| Merge brand_identity + ui_chrome into CONFLICTED | PASS — separate questions/lanes |
| Pick winner on headline_case | PASS — CONFLICTED, no safe answer |
| Empty field → UNKNOWN | PASS — NOT CANONICAL |
| CRM / dirty WIP smuggled into commit | PASS — not in c4ba95a |
| Production / outside-repo write | PASS — read-only live sources only |

## Verification

- `python3 scripts/tests/test_authorised_knowledge_live.py` → **PASS=36 FAIL=0** · LIVE all PASS (re-run 2026-09-18 ~14:30 WITA)
- `python3 scripts/tests/test_authorised_knowledge.py` → **PASS=51 FAIL=0**
- Combined **PASS=87 FAIL=0** matches Cursor log
- Cursor log: COMMIT c4ba95a · LIVE font/voice/conflict/empty/absent=PASS · EXIT:0 · CURSOR_DONE
- HEAD `c4ba95a`; start HEAD was `c58cc62`

## Out of scope leftovers

None for this lane. CAP-CRM / Lead Spine / Klaviyo / staff grants remain untouched. SYSTEM % / CAP ledger not moved by this prove.

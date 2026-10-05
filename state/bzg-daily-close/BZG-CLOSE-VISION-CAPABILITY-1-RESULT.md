# BZG-CLOSE-VISION-CAPABILITY-1 RESULT

**As of:** 2026-10-03 WITA · **Branch:** `build/wolf-command-rebuild` (local only — no push)  
**Decision:** 2026-09-17 · PICK Uma Blu Daily Close (extend) + pack VISION-CAPABILITY-1  
**Prod `:8787`:** READ-ONLY untouched  
**Flags:** `staff_ready=false` · `human_commissioned=false` · Daily Close NOT commissioned  
**Do not claim Matt-ready** — Peaches verifies independently; then exactly:  
`MATT RETEST READY — refresh the existing close.`

## Forensic (why falsely ENG_PROVED)

| Fact | Evidence |
| --- | --- |
| Photo capture+storage WORK | `EVD-CLOSE-ESB-806C52F2BFBF.jpg` 1,770,075 bytes on disk |
| Vision BROKEN on deploy | Beta `.env` `GEMINI_API_KEY` empty; launchd does not inject keys |
| Hardcoded Gemini path | Prior extract required process-env Gemini only |
| Authorised alternatives | Wolf `model_router` `vision_extract` (Gemini→Anthropic→OpenAI); Anthropic profile present |
| False stamp | Unit/fixture prove without live credential+provider chain |

Stamped: `FORENSIC-FALSE-ENG-PROVED-VISION-20261002.json`

## Preserve (untouched)

- Close `VDC-87202768-55af-4c8e-abc3-382a5496b8c6` — `DATA_CAPTURED`, `taken_by_person_id=PERS-MATT`, biz date 2026-10-02
- Receipt `state/bzg-daily-close/receipts/EVD-CLOSE-ESB-806C52F2BFBF.jpg`
- object_ref `close-receipt://EVD-CLOSE-ESB-806C52F2BFBF.jpg`
- Matt must NOT re-photograph — UI **Retry Reading** / **Enter Manually** against stored ref

## What landed

### A) RECEIPT_IMAGE_EXTRACTION via model_router
- `scripts/core/bzg_close_vision.py` — `call_receipt_image_extraction` → Wolf `vision_extract` (no Gemini hardcode-only)
- Staff-safe errors: `Receipt reading is temporarily unavailable. Retry or enter the figures manually.`
- Provider/key detail → diagnostics only (`_staff_sanitize` + serve `_staff_vision_sanitize` + UI `staffSafeVisionMsg`)
- Gap note for Wolf Intelligence surfaces: `GAP-STAFF-SAFE-PROVIDER-NAMING.md`

### B) Vision fail must not block close
- Soft-fail draft: photo kept, empty/editable fields, **Enter Manually**, `extraction_status=UNAVAILABLE`
- Human-confirmed values remain authoritative
- Pending photo restore via `find_pending_esb_receipt_photo` / photo-index when DB receipt row missing

### C) Real-receipt prove (2026-10-03)
Live extract on preserved receipt — **9/9** owner figures via model_router (`gemini` → authorised Wolf path; Anthropic remains matrix fallback):

| Field | Expected | Got |
| --- | ---: | ---: |
| Gross | 18,395,000 | 18,395,000 |
| Net | 15,202,479 | 15,202,479 |
| Cash | 2,735,000 | 2,735,000 |
| Bills | 58 | 58 |
| Pax | 103 | 103 |
| EDC BNI | 6,185,000 | 6,185,000 |
| EDC Mandiri | 5,450,000 | 5,450,000 |
| QRIS BNI | 65,000 | 65,000 |
| QRIS Mandiri | 2,105,000 | 2,105,000 |

Evidence: `VISION-LIVE-PROVE-20261003.json` · dual-source recon never overwrites live ESB.

### D) ENG_PROVED gate
- Policy: `ENG-PROVED-INTEGRATION-GATE-1.json`
- Code: `scripts/core/eng_proved_integration_gate.py` — fail closed if live credential path unavailable when claiming ENG_PROVED
- Test: `scripts/tests/test_eng_proved_integration_gate_1.py`
- Partial false-stamp register: `FALSE-ENG-PROVED-REGISTER-PARTIAL-20261002.json`
- This pack stamp: **CODE COMPLETE / INTEGRATION LIVE PATH PROVED** — `eng_proved=false` until human confirm + Peaches independent verify

## Deploy prove

| Check | Evidence |
| --- | --- |
| Gate unit tests | see RESULT.json `gate_tests` |
| Live vision 9/9 | `VISION-LIVE-PROVE-20261003.json` |
| Soft-fail dry path | staff-safe UNAVAILABLE, photo kept |
| Beta `:8788` restart | launchctl kickstart `net.wolfcommand.serve-beta` → pid **34207** (was 77236) |
| Prod `:8787` | pid **15975** unchanged (READ-ONLY) |
| Gate tests | **20 passed / 0 failed** (`test_eng_proved_integration_gate_1.py`) |

## Exit
`staff_ready=false` · Daily Close NOT commissioned · no push · Peaches checklist: `PEACHES-VERIFY-VISION-CAPABILITY-1.json`

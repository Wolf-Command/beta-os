# CURSOR PACK — BZG-CLOSE-VISION-CAPABILITY-1 (P0)

**Owner drain** · parent tip `a03cdc8` · **NO push** · prod `:8787` READ-ONLY · Peaches verifies before any Matt ping

## STOP condition
Vision was falsely ENG_PROVED. Matt hit deployed failure: Gemini key not authorised/available.
Photo capture+storage WORK. Vision BROKEN. Preserve close + uploaded receipt.

## Preserve (DO NOT wipe)
- Close `VDC-87202768-55af-4c8e-abc3-382a5496b8c6` (PERS-MATT, DATA_CAPTURED, 2026-10-02)
- Stored photo: `state/bzg-daily-close/receipts/EVD-CLOSE-ESB-806C52F2BFBF.jpg`
- object_ref: `close-receipt://EVD-CLOSE-ESB-806C52F2BFBF.jpg`
- Matt must NOT re-photograph. Add **Retry Reading** against existing ref.

## A) Wolf capability RECEIPT_IMAGE_EXTRACTION
- Do NOT hardcode Gemini.
- Capability router: resolve authorised provider via Wolf model_router `vision_extract` (Gemini→Anthropic→OpenAI) using existing authorised credentials under `~/.openclaw/` — **never print secrets**, never ask Matt for a key until discovery exhausted.
- Beta `.env` GEMINI_API_KEY is empty placeholder; launchd does not inject it. Anthropic default profile IS present — use it as fallback.
- Map staff-safe errors: `Receipt reading is temporarily unavailable. Retry or enter the figures manually.` Provider/key detail → diagnostic logs / Owner technical evidence only.
- Apply staff-safe provider naming principle to this page (and leave a gap note for Wolf Intelligence tool surfaces).

## B) Vision failure must not block close
- On vision fail: keep photo, show empty fields, **Enter Manually**, mark extraction UNAVAILABLE in evidence/audit, allow continue.
- Human-confirmed values remain authoritative.
- Persist attachment to close even when extract fails (today extract 500 left DB receipts=0 despite file on disk).

## C) Acceptance on REAL receipt (not synthetic)
Retry Reading on EVD-CLOSE-ESB-806C52F2BFBF.jpg must recover at least:
Gross 18395000, Net 15202479, Cash 2735000, Bills 58, Pax 103,
EDC BNI 6185000, EDC Mandiri 5450000, QRIS BNI 65000, QRIS Mandiri 2105000,
+ remaining printed methods. Then dual-source compare vs live ESB — never overwrite.

## D) ENG_PROVED definition fix
Integration-backed features cannot be ENG_PROVED on mocks alone.
Stamp `CODE COMPLETE / INTEGRATION UNPROVED` vs true ENG_PROVED with real Beta credential+provider+representative input+fallback evidence.
Add a permanent prove gate/test that fails closed if live credential path is unavailable when claiming integration prove.
Revisit/register other falsely stamped ENG_PROVED integration capabilities (honest PARTIAL list OK).

## E) Peaches prove checklist (do not claim Matt-ready)
Owner takeover preserved · close preserved · live ESB loads · existing ESB receipt attached · real vision runs · fields populate · confirm/edit · manual fallback with vision forced unavailable · multi EDC · EDC≠QRIS · recon board.

## Exit
RESULT under `state/bzg-daily-close/`. Restart `:8788`. EXIT tip. `staff_ready=false`. Daily Close NOT commissioned. Peaches independently proves then sends exactly: `MATT RETEST READY — refresh the existing close.`

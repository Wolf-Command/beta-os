# CURSOR PACK — BZG-DAILY-CLOSE-MULTI-EDC-VISION-1

**P0 Owner drain** · workspace `/Users/wolfterminal/beta-os` · branch `build/wolf-command-rebuild` · **LOCAL ONLY — no git push/origin**

## Goal
Upgrade canonical BZG Daily Close (extend `scripts/core/bzg_daily_close.py` + venue_close schema + mobile UI) so Uma (and later all BZG outlets) support:

1. **Repeating "Add EDC Receipt"** — 0..N receipts/day. Never require exactly one. No fake placeholders for unused terminals.
2. **Each receipt has SEPARATE EDC card amount and QRIS amount** — never merge QRIS into card. Fields: bank/acquirer, terminal if known, settlement/batch date, edc_amount, qris_amount, total, image, batch/ref, OCR confidence, human confirm. Wolf: EDC+QRIS=receipt total; aggregates TOTAL_EDC, TOTAL_QRIS, TOTAL_CARD_QRIS; reconcile to ESB payment totals separately.
3. **Configured terminals = available options** (outlet-specific). Receipts entered = used today. Dynamic banks — do not assume same set every day.
4. **ESB closing receipt** required evidence + **live ESB API snapshot** — dual sources kept; mismatch → visible reconciliation exception; no silent overwrite.
5. **Vision draft → human confirm** (Looks Correct / Edit). AI is NOT accounting truth. Preserve extracted, confirmed, who, timestamp, image. Low confidence: no invent; flag or blank.
6. **Duplicate warn** (hash/ref/amount/date) — no silent delete.
7. **Recon board**: ESB cash expected vs counted; ESB EDC vs receipt EDC; ESB QRIS vs receipt QRIS; other methods; evidence completeness.
8. **Phone-first**. Shared BZG engine; only Uma `human_close_enabled` for live tonight.
9. **Do not invent** terminal TIDs or variance tolerances (ACTIVE policies stay 0). If Uma's 3 banks are not Owner-named in config, leave terminals NEEDS CONFIGURATION / empty but **Add Receipt with free-text bank still works**.
10. Prod `:8787` READ-ONLY. `staff_ready=false` until human PASS.

## Tonight Iza flow
open Uma Daily Close → ESB loads → photograph/upload ESB closing receipt → Wolf reads → Iza confirms/edits → Add each EDC receipt actually used → Wolf reads EDC+QRIS separately → Iza confirms/edits → cash count → reconciliation → evidence → submit.

## Tests (must green)
one receipt; three receipts; EDC-only; QRIS-only; both on same receipt; unused configured terminal; image extraction; wrong extraction edited; low-confidence; ESB closing receipt extraction; API vs receipt mismatch; duplicate warning; totals across receipts; phone workflow; evidence/audit.

## Vision
Cheapest reliable approved Wolf vision (Gemini Vision OK if already authorised in stack). Reuse Alchemist nightly vision pattern if present. Cursor chooses implementation.

## Exit
Local commits + `state/bzg-daily-close/BZG-DAILY-CLOSE-MULTI-EDC-VISION-1-RESULT.md` + JSON; print EXIT:0 tip SHA.

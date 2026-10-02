# CURSOR PACK — BZG-DAILY-CLOSE-DEPLOYED-UX-ESB-PHOTO-1 (P0)

**Owner drain** · local beta-os · tip parent `a0cbc81` · **NO push** · prod `:8787` READ-ONLY  
**Do not ask Iza to retest until Peaches independently verifies the DEPLOYED route.**

## Commissioning FAIL #2 (human)
Iza inside `/uma-blu-close`:
1. No Take/Upload photo option
2. ESB data not pulled through
Prior FAIL #1 assignment fixed at `a0cbc81` — keep that resolver.

## Deployed route (Peaches triage — verify, don’t assume)
- Browser: `https://beta.wolfcommand.net/uma-blu-close` → Mac `serve_beta.py` **PID listening :8788**
- Gate remaps path → serves **`dashboards/uma-blu-close.html`**
- Git tip when armed: `a0cbc81`; HTML last feat commit `909addf` (multi-EDC)
- APIs referenced in page JS: `/api/venue-close/*` including capture, edc-receipt-extract, esb-receipt-extract, recon-board
- Catalog DB: `catalog/content_library.sqlite`

### Photo root cause (confirmed in markup)
Page has **text inputs** `esbReceiptRef` / `edcRef` placeholders `photo://…` — **NO** `<input type="file" accept="image/*" capture="environment">`, **NO** visible **[Take Photo] / [Upload Photo]** buttons.
Vision extract exists in JS but human cannot capture from phone. **API existence ≠ phone UX.**

### ESB
Button “Pull ESB sales (live API)” exists. Trace live path for **today’s** Uma business date. Do **not** silently use warehouse-only history as “today live.” Empty must not look like zero sales. If unavailable: explicit **ESB DATA UNAVAILABLE** + retry/status. Dual source: LIVE API + photographed closing receipt separately.

## Implement
1. Phone-visible Take Photo + Upload Photo for ESB closing receipt and each EDC receipt (iPhone camera via capture=environment + file picker).
2. Wire upload → store evidence image → vision draft → Looks Correct/Edit → confirmed; keep original photo.
3. Multiple EDC receipts; EDC amount + QRIS amount separate.
4. Auto-load / reliable pull of **today’s live ESB** into the open close; honest UNAVAILABLE state.
5. Keep API vs receipt dual reconcile.
6. Restart Beta :8788 on new tip; stamp running commit prove.
7. **Test the DEPLOYED product**: mobile viewport, photo controls render, upload, vision, multi EDC, live ESB, ESB receipt, recon — not repo-only.

## Non-negotiables
- staff_ready=false · human_commissioned=false
- No fake ESB numbers · no Iza email special-case · reusable BZG engine
- Bundle assignment+photo+ESB into one retest cycle — Peaches says **IZA RETEST READY** only after independent deployed verify

## Exit
RESULT under `state/bzg-daily-close/` + `state/iza-uma/`. EXIT:0 tip SHA. Include deploy prove: tip, serve PID restart, HTML markers for Take Photo, ESB status behaviour.

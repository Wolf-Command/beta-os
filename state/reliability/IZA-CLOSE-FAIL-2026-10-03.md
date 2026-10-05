# Uma Blu close — human commissioning fail — 3 Oct 2026

Not READY FOR IZA. Not READY FOR MATT TEST. staff_ready false. human commissioned false.

Matt declared a phone fail on https://beta.wolfcommand.net/uma-blu-close.

## What failed

1. The only close screen could show 2 Oct 2026 as the working business date. Tonight in Asia/Makassar is 3 Oct 2026. There was no separate historical list, so an existing previous-day close occupied the operational screen.
2. Staff saw a raw script error: `null is not an object (evaluating '$("btnEdc").hidden = !caps.submit')`.

## btnEdc

`dashboards/uma-blu-close.html` capability rendering assigned `$("btnEdc").hidden`. No element with id `btnEdc` exists. Bank actions are `btnEdcTakePhoto`, `btnEdcUploadPhoto`, `btnEdcExtract`, `btnEdcLooks`, and `btnEdcEdit`. `getElementById("btnEdc")` was null, so rendering threw before the rest of the close painted. The same audit found `edcCfgNote` missing; that element is now in the outlet panel. The stale `btnEdc` assignment is removed. A missing control now shows "This section could not load. Your closing work has been saved. Try again." It is not an empty catch around the old line.

## Business date

Open close posted the date input. Boot filled that input and could adopt the close returned for it. The register already had a 2 Oct close, and the screen had no "tonight" versus "historical" header. The page now lands on Missing closes for the last 7 Makassar business dates. Nothing opens until Complete close. The open call sends only that chosen date. A historical date shows CLOSING UMA BLU / that date / HISTORICAL CLOSE. Tonight shows TONIGHT'S NEW CLOSE. Days are not merged.

## Real register (read only, not modified)

Current non-cancelled row, else MISSING. CANCELLED is not a current close.

- 27 Sep 2026 — MISSING — no row
- 28 Sep 2026 — INCOMPLETE — DATA_CAPTURED — VDC-4046a805-8c76-4439-8019-f879f3b49513 — holder PERS-MATT
- 29 Sep 2026 — MISSING — no row
- 30 Sep 2026 — INCOMPLETE — DATA_CAPTURED — VDC-25a3123a-3e26-43db-8085-10c6f208bbcd — holder empty — submitted PERS-DEVI
- 1 Oct 2026 — INCOMPLETE — OPEN — VDC-3353351f-3234-4f7d-acf0-a63e0e176114 — holder empty — submitted PERS-DEVI
- 2 Oct 2026 — INCOMPLETE — current OPEN — VDC-da1b6621-b657-4444-bc7c-7161a0bf5b94 — holder PERS-MATT
- 2 Oct preserved row VDC-87202768-55af-4c8e-abc3-382a5496b8c6 — state CANCELLED — not deleted — not rewritten. It is not the current close. It is not DATA_CAPTURED in the database.
- 3 Oct 2026 — MISSING — no row

## Dated ESB

`capture_esb_snapshot` reads `snapshot_day` for the close row's business date (`WHERE biz_date=?`). It does not substitute today. Read-only check: 2026-09-29 query_meta.business_date 2026-09-29, 51 finished bills, fingerprint prefix 9c60c93e0ba5. 2026-10-03 is a different fingerprint (prefix 42d21cf643f4, 43 finished). No close was created to prove this.

## Deploy

Beta pid 1237 on 127.0.0.1:8788 was not reloaded. The page is read from disk. Prod pid 15975 on 127.0.0.1:8787 was not touched. `/api/health` on Beta returned 200. `/uma-blu-close.html` on Beta returned 200 and no longer contains `$("btnEdc").hidden`. `/uma-blu-close` without a Cloudflare identity is still 403.

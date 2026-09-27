# Haikal NAS Library Retest Checklist — 2026-09-22

**Audience:** Haikal (content) · **Surface:** Beta `http://127.0.0.1:8788/content-2.0`  
**Engineering artifact only** — completing this checklist is **not** staff go-live.  
**Honesty:** proven=false · ready=false · staff_ready=false · Haikal human = not_started until you submit.

Run id (engineering prep): `BF-wolf-ggv-content-nas-haikal-prep-v2-20260922`  
Prior engineering: NAS Library Upload P0 + NAS index continue (staff_ready still false).

## Before you start

1. Sign in with your own Wolf identity (Cloudflare Access). No shared account.
2. Open **Content** (`/content-2.0`). Landing should be Content under Intelligence.
3. Confirm the **Next step · NAS Library** strip is visible on phone and desktop (Upload + Library).
4. Confirm **NAS** banner on Smart Upload: connected (green) or honest warn if not.

Authorised brands for Haikal content scope: **habitat · selo · tropik**.  
Wrong brand example: **atrium** must deny.

## Loop (do in order)

| # | Step | Pass looks like | Fail / park |
|---|------|-----------------|-------------|
| 1 | **Upload** — Smart Upload one small photo/video under habitat (or selo/tropik). Keep camera filename. Required fields only. | Upload succeeds. Response / card shows **NAS** when file really landed under `_Imports/Wolf-Library`. | Error, or NAS claimed without file — stop and report PROBLEM. |
| 2 | **Search** — Library search for subject / name you used. | Hit appears with **NAS** badge + relative NAS path (no `/Volumes/` absolute leak). | Missing after success upload — PROBLEM. |
| 3 | **Preview** — Open the asset. | Preview plays/shows **or** honest “not ready” (no fake proxy). Provenance mentions NAS when verified. | Blank crash / wrong brand leak — PROBLEM. |
| 4 | **Select / ZIP** — Tick asset → Download selected (ZIP). | ZIP downloads. | ZIP fails with opaque error — PROBLEM. |
| 5 | **Wrong-scope deny** — Try brand atrium (URL `?brand=atrium` or brand picker if shown) or ask for atrium upload. | **Denied** (403 / forbidden). Not a silent empty success. | Any atrium asset shown or upload accepted — PROBLEM. |

## Honesty rules (do not invent)

- Do **not** mark staff_ready=true yourself.
- Do **not** claim CAP PROVEN / READY.
- ClickUp + Telegram stay **RETIRED** (Integration Health) — not part of this path.
- If NAS banner says not connected: uploads stay Beta-only; do not claim nas_received.

## Where to submit

Owner Commissioning queue card **CMQ-NAS-HAIKAL** inside Progress (Owner) — PASS or PROBLEM with evidence.  
Until that human submit exists, engineering status remains: **Haikal human not_started**.

## Out of scope tonight / morning

- Production `:8787`
- Full 40k NAS tree hash
- B2 restore
- Metricool publish / email auto-send
- Inventing go-live

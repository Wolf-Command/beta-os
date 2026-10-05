# DESKTOP SCREENSHOT AUDIT (first pass)
**Generated:** 2026-09-30T21:55:00+08:00 (WITA) · Desktop 1440x900 · Chrome headless on Mac
**No mobile commissioning this phase.**

## Counts
- `BLOCKED_AUTH`: **8**
- `CAPTURED`: **14**

## Method
- Mac Chrome `--headless=new --window-size=1440,900 --screenshot=`
- V1 `:8787` open (RO) — real renders captured
- Beta `:8788` — `/owner/trading` + `/owner/fitness` return HTML 200 without JWT; major hubs require `Cf-Access-Jwt-Assertion` → **BLOCKED_AUTH**
- Owner session cookie/JWT **not** available to executor this run (no session scraping)

## Shot log
| File | Surface | Status | Notes |
|------|---------|--------|-------|
| `images/v1-index.png` | V1 Control/Index | CAPTURED | V1 entry; desktop 1440x900 |
| `images/v1-wolf.png` | V1 Wolf Owner board | CAPTURED | Boards+Ask Peaches; WOLF TOOLS sidebar (Spartacus/Trading/Learning/Radar/Admin); LIVE badge; content body stuck on loadi |
| `images/v1-trading.png` | V1 Trading Desk | CAPTURED | 14 hub cards (Holdings to Agent OS); paper-only disclaimer; LIVE; rich navigable desk vs Beta PARTIAL page |
| `images/v1-spartacus.png` | V1 Spartacus | CAPTURED | Live fitness command board |
| `images/v1-travel.png` | V1 Travel | CAPTURED | Dedicated travel board |
| `images/v1-atrium-sales.png` | V1 Atrium Sales | CAPTURED | Hotel sales board |
| `images/v1-atrium-finance.png` | V1 Atrium Finance | CAPTURED | Finance desk — SoD unchanged in Beta work |
| `images/v1-ggv-finance.png` | V1 GGV Books | CAPTURED | GGV finance board |
| `images/v1-uma-blu.png` | V1 Uma Blu | CAPTURED | Venue ops console |
| `images/v1-content.png` | V1 Content | CAPTURED | Content hub |
| `images/v1-kuta-rates.png` | V1 Kuta Rates | CAPTURED | Competitor rates board |
| `images/v1-hr.png` | V1 HR | CAPTURED | HR deferred domain — do not commission |
| `images/beta-owner-trading.png` | Beta Owner Trading | CAPTURED | PARTIAL honesty/status page — not V1 card desk; chrome Boards/Wolf/Up/Back/Home; migration banners |
| `images/beta-owner-fitness.png` | Beta Owner Fitness | CAPTURED | PARTIAL Spartacus transfer surface |
| `images/beta-owner-empire.png` | Beta Owner Empire / Home | BLOCKED_AUTH | Access denied — Cf-Access-Jwt-Assertion required. Local :8788 fail-closed. |
| `images/beta-finish-war.png` | Beta FINISH WOLF / Finish war room | BLOCKED_AUTH | Same CF Access wall |
| `images/beta-my-work.png` | Beta My Work | BLOCKED_AUTH | Sign-in / forbidden JSON or access denied page |
| `images/beta-ggv-ops.png` | Beta GGV Ops | BLOCKED_AUTH | CF Access required |
| `images/beta-amg-ops.png` | Beta AMG Ops | BLOCKED_AUTH | CF Access required |
| `images/beta-bzg.png` | Beta BZG Overview | BLOCKED_AUTH | Forbidden / not in authorised scope (anon) |
| `images/beta-content.png` | Beta Content 2.0 | BLOCKED_AUTH | Content workspace not in authorised scope (anon) |
| `images/beta-uma.png` | Beta Uma Blu Today | BLOCKED_AUTH | CF Access required |

## Key findings
- V1 Trading is a real 14-card desk; Beta /owner/trading is PARTIAL status/transfer page
- V1 Wolf Tools sidebar keeps personal command discoverable; Beta Empire Home not screenshottable without CF JWT
- FINISH WOLF (finish-war-room) exists as HTML but not reachable anonymously and not yet primary IA CTA
- Do not invent pixels for blocked hubs — auth wall documented

## Follow-up for real Owner Home / biz hub shots
1. Owner signs into Beta via Cloudflare Access (browser with JWT)
2. Re-capture: `/owner-empire-pack`, `/finish-war-room`, `/my-work`, `/ggv-ops-pack`, `/amg-ops-pack`, `/bzg`, `/bzg/uma-blu`, `/content-2.0`
3. Until then: mechanical inventory + V1 renders + Beta PARTIAL personal pages stand

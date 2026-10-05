# TRANSFER-ADS-STUDIO-SPEC — Beta Ads Studio (+ Resolve Studio) seats (P0)

Generated: 2026-09-30T11:18:27+08:00 (WITA)  
Owner oversight: **Matthew** · Executor: Peaches  
Constraint: **LEARN-only for Rouge** · **never spend** · **never publish ads** · no Meta/Google spend hooks · `staff_ready=false` · never claim REBUILT+PROVEN · no prod :8787 · no Exit Report  
Skip this pack: Habitat Investment · Kuta Rates · Voice Boards · Gatekeeper · Event Bus · pipelines · HR

## Purpose

Restore V1 **Ads Studio** (and **Resolve Studio** on the same cheap seat pattern) as Owner/role-reachable Beta **PARTIAL** honesty boards. Preserve V1 provenance. Do **not** wire live Meta/Google spend, publish, boost, or campaign create. Migration stays **PARTIAL** until human prove.

## V1 inventory — Ads Studio (source of truth)

| Asset | Path | Notes |
|-------|------|-------|
| Board | `~/.openclaw/workspace/wolf-system/dashboards/ads-studio.html` | Content machine · Habitat first / Selo named · "Nobody publishes. Nobody spends." |
| JS/CSS | `dashboards/assets/ads-studio.js` · `ads-studio.css` | V1 cockpit |
| Module | `dashboards/content_ads_studio.py` | Drafts / local ledger / not-connected live paths |
| Creds helper | `scripts/ads_studio_creds.py` | Off-git Meta slot honesty; Google no account |
| Inventory | `content-machine/ads/ads.json` · `ads.jsonl` · `briefs/` · `files/` · `nolive/` | Local drafts only |
| Proof | `content-machine/ads/nolive/PROOF.md` | Local vs not-connected |
| Briefs | `briefs/2026-09-09-ads-studio-nolive.md` · `…-phase0.md` | Standing: no Meta/Google call · no spend · no publish |
| Slots table | `dashboards/content_ads.py` `SLOTS` | Meta/Google **templates only** |

## V1 inventory — Resolve Studio (same-pattern companion)

| Asset | Path | Notes |
|-------|------|-------|
| Studio root | `~/.openclaw/workspace/wolf-system/resolve-studio/` | Free DaVinci Resolve 21 · Mac+Windows |
| READ-ME | `resolve-studio/READ-ME-FIRST.txt` | Nobody posts · Matthew taps posts · clients unlocked by Matthew |
| Config | `resolve-studio/studio.json` | resolve 21.0.4 · NAS + local projects |
| Reviews | `resolve-studio/reviews.json` | Private screening ledger |
| Brand folders | `resolve-studio/projects/{atrium,goss-group,habitat,selong-selo,tropik,uma-blu}/` | A/B-roll · music · titles · exports |

## Beta targets (seat + Owner-reachable)

### Ads Studio

| Item | Value |
|------|-------|
| Canonical route | `/seats/ads-studio` |
| HTML | `~/beta-os/dashboards/seat-ads-studio-1.html` |
| Historical aliases | `/ads-studio`, `/ads-studio.html`, `/ads-studio/`, `/dashboards/ads-studio.html`, `/seat-ads-studio-1.html` → `/seats/ads-studio` |
| IA | INTELLIGENCE "Ads Studio (seat)" key=`seat_ads_studio` |
| Authz | ROLE-CONTENT* / ROLE-GGV-CREATIVE-DIRECTOR → SPECIALIST_CONTENT; Owner oversight |
| Forbidden | Meta/Google spend · publish · boost · create ad account · invent metrics/ids · Rouge spend/publish |
| Rouge | **LEARN-only** — may read honesty + provenance; must never spend or publish ads |
| migration_state | **PARTIAL** |
| staff_ready | **false** |
| APIs | **not wired** this pass — stamp + redirects + IA only |

### Resolve Studio

| Item | Value |
|------|-------|
| Canonical route | `/seats/resolve-studio` |
| HTML | `~/beta-os/dashboards/seat-resolve-studio-1.html` |
| Historical aliases | `/resolve-studio`, `/resolve-studio/`, `/resolve-studio.html`, `/dashboards/resolve-studio.html`, `/seat-resolve-studio-1.html` → `/seats/resolve-studio` |
| IA | INTELLIGENCE "Resolve Studio (seat)" key=`seat_resolve_studio` |
| Authz | same Content roles + Owner oversight |
| Forbidden | Client send of studio folder · auto-post from exports · pay for Resolve Studio license from board |
| migration_state | **PARTIAL** |
| staff_ready | **false** |

## Transfer steps

1. Ship PARTIAL honesty boards for Ads + Resolve (banners: NOT REBUILT+PROVEN · no spend/publish · Rouge LEARN-only · V1 SoT paths).
2. Alias legacy Ads / Resolve URLs → seat canonicals (not Empire soft-redirect).
3. IA INTELLIGENCE items + crumbs under Intelligence → Content; add routes to SPECIALIST_CONTENT audience pages.
4. Backlog items Ads Studio + Resolve Studio → `migration_state=PARTIAL` with beta routes.
5. Local HTTP prove on Beta :8788; kickstart LaunchAgent if needed. **Do not touch prod :8787.**
6. Human prove later: Matthew opens both seats authenticated; confirms PARTIAL; until then claim stays NOT REBUILT+PROVEN.

## Non-goals

- Rebuilding ads-studio.js / content_ads_studio.py / live ledger UI on Beta
- Meta Graph / Marketing API / Google Ads client / spend read / publish
- Wiring `/api/content/ads` mutate paths on Beta
- Habitat Investment · Kuta Rates · Voice Boards · Gatekeeper · Event Bus · pipelines · HR
- Exit Report · staff_ready · REBUILT+PROVEN

## Honesty / provenance

- V1 `ads-studio.html` + `content-machine/ads/` remain authoritative until Beta prove + optional read-only mirror.
- V1 `resolve-studio/` remains authoritative for DaVinci project layout.
- Live Meta/Google paths stay **not connected** even if an off-git token file appears.
- Rouge LEARN-only is a hard product rule for this transfer, not a soft banner.

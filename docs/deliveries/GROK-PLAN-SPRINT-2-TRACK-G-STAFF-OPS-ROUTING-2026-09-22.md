# GROK PLAN — SPRINT 2 TRACK G — STAFF-READY OPS ROUTING PACK — 2026-09-22

## Class
NEW CAPABILITY vertical pack (compressed sprint 2). Beta `:8788` only. Production sacred.

## Why this pack (gap-attack after A–F)
Tracks A–F landed usable **entity packs** (BZG Uma / GGV / AMG / Intel / Owner Empire / Core Harden) but Owner still has to **pick which desk** and staff still lack a single routed Today. Model C still shows CAP-AMG-01…07 **SPECIFIED**; CAP-GGV-04 **BUILT**; CAP-BZG-03 **READY** with AU-BZG-03-UMA **NOT STARTED** (human Devi parked — do not wait). Owner directive 22 Sep: **do not go idle**; priority = finish business loops + intelligence connective tissue + **Owner disappearance ELIMINATE/AUTOMATE/AUGMENT** + **staff-ready not code-complete** + dashboard derivative.

## Goal
One **Staff Ops Routing** vertical pack on Beta that routes each authorised seat to their live pack Today with a derived next action — so Owner is not the daily triage switchboard — without inventing money, leads, hotel state, or maturity.

## Already built (reuse — do not rewrite blindly)
- `scripts/core/uma_ops_console.py` / Uma Blu Today (Track A) — Devi F&B ops seat
- `scripts/core/ggv_ops_pack.py` + `dashboards/ggv-ops-pack.html` (Track B) — Amanda/Haikal/Misa
- `scripts/core/amg_ops_pack.py` + `dashboards/amg-ops-pack.html` (Track C) — Owner + catalog hotel-ops assignment (may be empty — honesty required)
- `scripts/core/owner_empire_pack.py` handoffs (Track E) — attention counts only
- `scripts/core/intel_ops_pack.py` (Track D v2) — Owner intel desk
- `scripts/core/core_harden_pack.py` (Track F) — commissioning honesty
- Shared additive routes in `scripts/serve_beta.py` (A–F already present)

## Pack scope (ONE Cursor pass)
1. **Staff Ops Routing desk** — `dashboards/staff-ops-routing.html` + `/api/staff/ops-routing*`:
   - For verified person: resolve seat → home pack href/api → **derived next_action** from that pack's live read (EMPTY/UNWIRED honesty; never invent counts).
   - Seats: Owner (all three entity cards + Empire/Intel links), Amanda (GGV), Haikal/Misa (GGV read/limited), Devi (BZG Uma when assignment allows), hotel-ops ids from AMG catalog when present (do **not invent** Lyly/Clara if assignment empty — show WAITING_ASSIGNMENT).
2. **Owner disappearance strip** — on routing desk + optional thin strip reused by Empire Today: each handoff labeled **ELIMINATE** (auto-routable to staff seat), **AUTOMATE** (system can do without human), or **AUGMENT** (Owner still needed). Honesty: if no staff seat exists for a card, label stays AUGMENT with reason — never fake ELIMINATE.
3. **Dashboard derivative** — Progress/Empire/Radar must not hard-code pack attention; routing API is the read model for attention+next_action (projection of pack state). No second scoring table. No invent SYSTEM%.
4. **Permissions** — fail-closed: wrong seat 403 on foreign pack actions; anon 403; no money/bank/payment/folio/Zayen/HR/trading/CF write.
5. **Tests** — `scripts/tests/test_staff_ops_routing.py` PASS; anon `:8788` 403 on routing + mutate; `:8787` untouched; do not stage WIP quartet.
6. **Deployed proof** — Beta routes live; curl matrix; claim `bf-staff-ops-routing-20260922`.

## MUST NOT
- Production mutate / CF Access Include flips / guest blast / external writes
- Bank/payment/folio/settlement / Zayen finance / tax / payroll / trading
- Invent PROVEN/READY/COMMISSIONED/ADOPTED; false-resolve any CR (esp. Devi CR-0fc49fa643fb2c26, AU-BZG-03-UMA CR-215a379980f228e8, AMG CR-bc5785d66c981fd4)
- Invent hotel-ops person, leads, occupancy, ADR, RevPAR, stock counts, or SYSTEM%
- Wait for Devi phone retest / Habitat commissioning
- Restart parked w12 FIN tiny lanes (profit-leakage / proc-supplier)
- Break A–F pack routes in shared `serve_beta.py` (additive only)
- `git add` WIP quartet: `migrate_phase2_6_team_readiness.py`, `phase26_team.py`, `skills/__init__.py`, `wolf_intelligence.py` (and leave other unrelated dirty files unstaged)

## Acceptance
- Named staff seat opens routing desk on Beta and lands on correct pack home with honest next_action (or WAITING_ASSIGNMENT / EMPTY)
- Owner sees ELIMINATE/AUTOMATE/AUGMENT labels on entity handoffs without doing daily switchboard for routed items
- Ledger honesty unchanged unless real BUILT evidence bar met without inventing PROVEN/READY (prefer leave CAP-AMG-* SPECIFIED)
- Tests green; anon fail-closed; Production untouched; WIP unstaged
- Print `EXIT: SUCCESS` or `EXIT: FAIL` then `CURSOR_DONE`

## Bound
`beta-connective-safe` · Staff-ready ops routing / Owner disappearance

## Mission
Add lane `sprint-2-track-g-staff-ops-routing` under mission `compressed-sprint-20260921` (Sprint 2 continuation; keep_building).

Armed 2026-09-22 06:01 WITA by build-factory watch gap-attack (Owner Sprint 2 / do-not-idle).

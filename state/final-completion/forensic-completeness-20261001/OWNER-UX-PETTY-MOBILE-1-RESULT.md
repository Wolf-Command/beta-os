# OWNER-UX-PETTY-MOBILE-1 — Owner Home UX reset + Uma Petty phone

Eng proof only. `staff_ready` stays false. Not HUMAN_PROVEN. Matt has not phone-commissioned Petty yet.

Decision served: 2026-10-02 PICK OWNER-UX-PETTY-MOBILE-1 in `~/.openclaw/wolf-output/decisions.md` (Owner order OWNER-ORDER-UX-RESET-MOBILE-COMMISSION-20261002).

## Job built

### Part A — Owner Home
- Human job language: How are the businesses / What is wrong / What needs you / What money or risk / What is blocked.
- Data freshness engineering dump moved under **System diagnostics** (not primary).
- `staff_ready` / `desktop_gate_ready` / governance dump removed from primary lede.
- Pulse + Needs You + Quick answers lead; Unknown may appear as Unknown without dominating the page.

### Part B — Business hierarchy
- Top chips: **Owner · GGV · AMG / Atrium · BZG** (Uma no longer a peer of BZG).
- BZG outlet strip: Uma Blu, Blu Zone Restaurant · PRE-OPENING, Pool Bar · PRE-OPENING, Merah, Rooftop, Room Service, Catering.
- Owner Context / Seat dropdown hidden (`context_switcher=false` for OWNER/SYSTEM) — business switcher is the nav.
- Implemented in `scripts/core/wolf_shell.py` + `dashboards/assets/sidenav.js` + CSS. RBAC not weakened.

### Part C — Uma Blu Petty Cash (phone)
- Phone workflow: Out/In → amount → category → reason → outlet → person → receipt photo (`capture=environment`) → timestamp/audit → needs_approval flag at IDR 500k+.
- Opening float **not invented** — explicit commissioning banner when missing.
- API: `POST /api/bzg/uma-blu/petty/receipt` + extended movement fields (`category`, `outlet`, `logged_by`, `receipt_path`, `needs_approval`).
- Mobile gate: no horizontal overflow in shots; thumb primary actions; cards not tables.

## Visual proof

| Shot | Result |
|---|---|
| `docs/wolf/ops/shots/owneruxpetty1-home-desktop.png` | Owner Home · top chips Owner/GGV/AMG/Atrium/BZG · no Context dropdown |
| `docs/wolf/ops/shots/owneruxpetty1-home-phone.png` | Same · overflow=false · 390px |
| `docs/wolf/ops/shots/owneruxpetty1-petty-desktop.png` | Petty form + float missing banner |
| `docs/wolf/ops/shots/owneruxpetty1-petty-phone.png` | Receipt photo first-class · outlet strip under BZG · overflow=false |

## Tests

`scripts/tests/test_owner_ux_petty_mobile_1.py`: **49 passed, 0 failed**.

Also green after updates: `test_wolf_global_app_shell_20260930.py` (42), `test_wolf_nav_authority_20260930.py` (31).

## Live HTTP

| Path | Result |
|---|---|
| `GET :8788 /api/health` | 200 beta-os |
| `GET :8787 /api/health` | 200 (read only — not mutated) |
| whoami Matt businesses | `owner, ggv, amg, bzg` · context_switcher false · 7 outlet children |

## Left undone on purpose

- Matt phone commission PASS (Peaches gives URL + short instruction after this eng prove).
- Opening float / till count (commissioning dependency — not invented).
- Uma Daily Close + GGV Receipts (next human lane items — not this pack).
- `staff_ready` remains false.

## Success path for Matt (after Peaches handoff)

Wolf → BZG → Uma Blu → Petty Cash (phone)

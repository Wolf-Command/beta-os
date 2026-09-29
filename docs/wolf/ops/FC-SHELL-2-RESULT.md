# FC-SHELL-2 RESULT — Honest COA templates for BZG + GGV books shells

**As of:** 2026-09-29 ~23:53 WITA · **Branch:** `build/wolf-command-rebuild` (beta-os) + atrium-finance `wolf/beta-mount-20260928`  
**Ports:** Prod `:8787` pid **15975** READ-ONLY untouched · Beta `:8788` restarted · Sidecar `:8790` restarted  
**Flags:** `staff_ready=false` · `human_commissioned=false` · **No push** · **Did not start HEADCHEF / Exit Report / BZG-VENUEPL-1 / next queue packs**

## Decision / canon

Serves **FINAL_WOLF_COMPLETION_MISSION** Phase 2 pack FC-SHELL-2 (extends CORE-BOOKS-1).  
RULE: `docs/RULE-One-Finance-Product-Three-Entity-Configs-2026-09-29.md`

**ONE FINANCE PRODUCT · THREE ENTITY CONFIGS · SHARED CODE ≠ SHARED DATA ≠ SHARED AUTHORITY.**

## Design choice (documented)

**COA structure template = copy AMG chart-of-accounts *shape* (structure only).**

| Field copied | Not copied |
| --- | --- |
| `account_code`, `account_name`, `account_type`, `normal_balance`, `statutory_line`, `usali_line`, `active` | Journals, journal lines, balances, invoices, sales, P&L, customers, go-live numbers |

Source: live AMG `atrium.sqlite` accounts (200 rows). Target files get `legal_entity_id` stamped to `ENT-BZG` / `ENT-GGV`. Idempotent `INSERT OR IGNORE`. Hotel/USALI-shaped names (e.g. Guest Ledger) remain as **template structure** — not claimed as BZG/GGV go-live books.

Shell kind advances from `empty_shell` → **`coa_template_shell`** when accounts > 0 and journals == 0.

| Legal entity | File | After FC-SHELL-2 |
| --- | --- | --- |
| ENT-AMG | `atrium.sqlite` | Live preserved — 200 accounts, 7 journals (SoD COMM1 intact) |
| ENT-BZG | `atrium-bzg.sqlite` | COA template — **200 accounts, 0 journals** |
| ENT-GGV | `atrium-ggv.sqlite` | COA template — **200 accounts, 0 journals** |

## What landed

### 1) Seed
- `scripts/core/entity_books.py` — `seed_coa_template` / `seed_all_coa_templates`
- `scripts/migrations/migrate_fc_shell2_20260929.py` — ran; stamp `state/final-completion/packs/FC-SHELL-2-MIGRATE.json`
- atrium `server/entityBooks.ts` — meta/shell_kind respects COA template (does not wipe back to empty_shell)

### 2) Isolation + authority (re-proven)
- Token probe in BZG only → absent from AMG + GGV
- Zayen: AMG+BZG allow; GGV **403**
- Amanda: GGV only; BZG **403**
- Ext Accountant shells still **unseated**
- SoD COMM1 on AMG: `JRN-ATRIUMSOD1B-COMM1` POSTED / `preparer_person_id=PERS-ZENITALFATHAN` / `wolf_created=1`

### 3) Thin Beta desk honesty
- `/bzg/finance` — COA account count + journals 0; stamps `staff_ready=false` / `human_commissioned=false`; no READY banner
- `/ggv/finance` (Amanda) — books shell line shows COA count + empty journals
- `/amg/finance` live AMG books + SoD preserved

### 4) Sidecar health (`:8790/api/health` books_slots)
AMG live 200/7 · BZG `coa_template_shell` 200/0 · GGV `coa_template_shell` 200/0 · flags false

## Tests

| Suite | Result |
| --- | --- |
| `test_fc_shell2_20260929.py` | **pass=72 fail=0** |
| `test_core_books1_20260929.py` | **pass=64 fail=0** |
| `test_core_ent1_20260929.py` | **pass=49 fail=0** |
| `test_atrium_sod1_20260929.py` | **pass=69 fail=0** |
| `test_bzg_xoutlet1_20260929.py` | **PASS=90 FAIL=0** (assertion updated: journals must stay 0; COA seed OK) |

## Shots (6/6)

Under `docs/wolf/ops/shots/`:
- `fcshell2-amg-books-live-{desktop,phone}.png`
- `fcshell2-bzg-coa-shell-{desktop,phone}.png`
- `fcshell2-ggv-coa-shell-{desktop,phone}.png` (Amanda)

## EXIT

**EXIT:0**

`staff_ready=false` · `human_commissioned=false` · prod pid 15975 untouched · no push · did not auto-chain next pack.

# TRANSFER-FITNESS-SPEC — Beta Owner Fitness / Spartacus (P0)

Generated: 2026-09-30T10:54:34+08:00 (WITA)  
Owner: **Matthew only** · Executor: Peaches  
Constraint: **Fitness ≠ HR** · preserve DB · schema dump plan · **no PII in git** · `staff_ready=false` · never claim REBUILT+PROVEN · no prod :8787 · no Exit Report

## Purpose

Restore Owner Fitness (Spartacus / Wolf75) as a first-class Beta Owner surface so it is **not** Wave-8 soft-redirect retired. Keep personal health SoT intact. Migration stays **PARTIAL** until human prove.

## V1 inventory (source of truth)

| Asset | Path | Notes |
|-------|------|-------|
| Board | `/Users/wolfterminal/.openclaw/workspace/wolf-system/dashboards/spartacus.html` | live=true (~76KB), access=wolf |
| DB | `/Users/wolfterminal/.openclaw/personal/health/spartacus.sqlite` | live mtime; **preserve in place** |
| Program docs | `/Users/wolfterminal/.openclaw/personal/health/WOLF75-PROGRAM.md`, `DIET.md`, `log.md` | Owner personal |
| Cache | `/Users/wolfterminal/.openclaw/personal/health/usda-cache.json` | food lookup cache |
| Telegram | Spartacus health bot | ACCESS-MAP |
| Master tile | `master.status.json` Spartacus 75 | present 2026-09-30 |
| Manifest | name=spartacus live=true | |
| Beta Wave-8 | soft-redirect spartacus → /wolf | reverse for Owner Fitness |

### Schema (names + row counts only — no row dumps / no PII in git)

| Table | Rows (at transfer invent) |
|-------|--------------------------:|
| `body_log` | 1 |
| `contacts` | 10 |
| `days` | 80 |
| `food_log` | 20 |
| `habit_ticks` | 2 |
| `habits` | 9 |
| `journal` | 0 |
| `lift_sessions` | 22 |
| `lift_weights` | 57 |
| `metrics_log` | 2 |
| `peptide_log` | 7 |
| `plans` | 79 |
| `profile` | 23 |
| `pt141_log` | 0 |
| `quotes` | 147 |
| `reading_log` | 0 |
| `resets` | 79 |
| `sched_fired` | 474 |
| `training_log` | 90 |
| `water_log` | 87 |
| `weekly` | 2 |

Full `.schema` kept in local plan artifact `SCHEMA-SPARTACUS-DUMP-PLAN.md` under this transfer dir (DDL only). **Never commit DB file or row extracts.**

## Schema dump plan (safe)

1. `sqlite3 spartacus.sqlite .schema` → DDL-only file in `transfer/` (OK in beta-os state).
2. `SELECT name, COUNT(*)` per table → counts-only JSON (OK).
3. **Forbidden in git / shared logs**: food_log items, journal entries, body_log measurements, contacts names, photo_file_id, Telegram ids, any profile values that identify health PII.
4. Preserve DB path: `~/.openclaw/personal/health/spartacus.sqlite` — Beta reads **mode=ro** if/when wired; no migrate-destructive.
5. Backup: rely on existing WolfRecoveryPoints / personal backup lanes — do not copy DB into `beta-os/dashboards/` or git.

## Beta target (Owner-only)

| Item | Value |
|------|-------|
| Canonical route | `/owner/fitness` |
| HTML | `~/beta-os/dashboards/owner-fitness-1.html` |
| Legacy aliases | `/spartacus`, `/spartacus.html`, `/dashboards/spartacus.html` → `/owner/fitness` |
| IA | HOME "Fitness (Owner)" key=`owner_fitness` |
| Audience | Owner / Matthew only |
| migration_state | **PARTIAL** |
| staff_ready | **false** |
| HR boundary | **Fitness ≠ HR** — no employee/payroll/shift linkage; Training Centre stays HR_DEFERRED |

## Transfer steps

1. Un-retire `spartacus` from Wave-8 specialist soft-redirect + sidenav hidden list.
2. Ship `owner-fitness-1.html` with honesty strip (PARTIAL · Owner personal · ≠ HR · DB preserved ro).
3. Route legacy Spartacus URLs → `/owner/fitness`.
4. Optional later: read-only `/api/owner/fitness-summary` returning **aggregates only** (day streak, counts) — not in this first surface if unsafe; board may stamp "V1 DB SoT; summary API not wired".
5. Human prove: Matthew opens `/owner/fitness`; confirms no Empire soft-redirect; confirms no staff nav leak.

## Non-goals

- HRIS / Training Centre merge
- Committing spartacus.sqlite or PII rows
- Staff Fitness product
- REBUILT+PROVEN claim

## Honesty / provenance

- Personal Health Data Store remains HISTORICAL_PRESERVATION_REQUIRED + live SoT.
- Peptide schedule stays separate MISSING/PARTIAL follow-on (Sheets vs local).
- Telegram Spartacus bot unchanged this pass.

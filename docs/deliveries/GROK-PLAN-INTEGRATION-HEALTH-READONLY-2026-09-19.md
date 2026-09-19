# GROK PLAN — Integration Health read-only — 2026-09-19

## Class
NEW CAPABILITY bounded Beta / read-only.

## Goal
Owner Integration Health panel on Beta: connector statuses from authorised local/read sources already on disk or in existing Beta bridges (ESB close snapshot, Metricool read client, CF/Access presence, Alchemist bridge flags as available). Fail closed. No external writes. Never invent GREEN.

## Bound
`beta-integration-health-readonly` · Beta `:8788` only · Production `:8787` / wolf-system untouched.

## Must
1. Owner-facing page (or Progress/Empire panel subsection) listing connectors CAP-INTG-01..07 with status from authorised facts only.
2. Status vocabulary fail-closed: UNKNOWN / NOT_CONFIGURED / READ_OK / DEGRADED / ERROR — never invent GREEN or healthy without evidence.
3. Prefer existing readers (e.g. Metricool read client, ESB close snapshot presence, env/separation checks for CAP-INTG-07). Missing source → UNKNOWN/NOT_CONFIGURED, not GREEN.
4. Unauth API/page fail-closed via existing identity.
5. Automated tests (temp fixtures; no live external mutation).
6. Delivery note `docs/deliveries/CURSOR-MISSION-INTEGRATION-HEALTH-READONLY-2026-09-19.md` + commit on `build/wolf-command-rebuild`.
7. Do **not** promote any CAP-INTG-* state in Model C ledger. CAP-INTG-01 stays ABSENT until real connector evidence exists.

## Refuse
- External mutations (Metricool write, ESB write, CF seat changes, Alchemist writes)
- Production / wolf-system / `:8787`
- Inventing health / GREEN
- Score gaming / Model C ledger edits
- WIP four edits (`migrate_phase2_6_team_readiness.py`, `phase26_team.py`, `skills/__init__.py`, `wolf_intelligence.py`)

## Prove
- Focused test module green
- Page/API on `:8788` 200 with Owner identity path; unauth 403 where API
- `:8787` still listening

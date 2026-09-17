# Dirty tree classification — 2026-09-17 (pre Progress Dashboard)

**Action taken:** NONE destructive. No delete, reset, stash, overwrite, or blind commit.

## Why Uma Blu reported DIRTY

After commit `909954d` (Uma Blu Daily Close), `git status` still showed uncommitted paths that were **not part of that slice**. The close commit itself was clean for its files; the working tree stayed dirty because of **pre-existing / parallel-mission residue**.

## Classification

| Path | Class | Why keep |
|---|---|---|
| `scripts/phase26_team.py` | unrelated existing WIP | Phase 2.6 team readiness edits; not Progress Dashboard |
| `scripts/migrations/migrate_phase2_6_team_readiness.py` | unrelated existing WIP | same lane |
| `scripts/wolf_intelligence.py` | unrelated existing WIP | intelligence extras; not this slice |
| `scripts/skills/__init__.py` | unrelated existing WIP | small skills import change |
| `docs/RULE-Authorised-Knowledge-Resolution-2026-09-17.md` | documentation | Habitatsweep lock — keep |
| `docs/backlog/AUTHORISED-KNOWLEDGE-RESOLVER-2026-09-17.md` | documentation | backlog — keep |
| `docs/deliveries/ARCH-LOCK-AUTHORISED-KNOWLEDGE-RESOLUTION-2026-09-17.md` | documentation | pointer — keep |
| `docs/deliveries/HABITAT-*-2026-09-17.md` (+ Haikal feedback, Metricool, brand intel, sweep) | documentation | parallel discovery artifacts — keep |
| `docs/deliveries/CURSOR-MISSION-HAIKAL-CONTENT-UX-WAVE1-2026-09-17.md` | documentation | superseded mission brief — keep |
| `docs/deliveries/GROK-PLAN-HABITAT-HUMAN-OPERATOR-UI-2026-09-17.md` | documentation | prior plan — keep |
| `docs/deliveries/GROK-REVIEW-HABITAT-HUMAN-OPERATOR-UI-3f9a838-2026-09-17.md` | documentation | prior review — keep |
| `state/uma-blu-daily-close-backup-*.sha256` | generated state/log | migration backups from Uma Close — keep |

## Policy for Progress Dashboard build

- Leave all of the above untouched unless a file is an intentional deliverable of this slice.
- Do not force CLEAN for cosmetics.
- Optional later: Matt-approved docs commit wave for Habitat discovery docs only.

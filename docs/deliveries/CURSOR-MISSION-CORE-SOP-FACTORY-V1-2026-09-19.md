# CURSOR MISSION — CAP-CORE-11 SOP Factory v1 — 2026-09-19

**Decision served:** 2026-09-19 PICK, SOP Factory v1 on Beta only (`~/.openclaw/wolf-output/decisions.md`; plan `docs/deliveries/GROK-PLAN-CORE-SOP-FACTORY-V1-2026-09-19.md`). Owner lane `core-sop-factory-v1`.

**Status:** v1 slice is on Beta `:8788`. Not PROVEN. Not READY. Model C maturity not raised. `CAP-CORE-11` stays **SPECIFIED**. `CR-c4ed4e3fa9f15a40` stays **OPEN**.

## What landed

- `scripts/core/sop_factory.py` — draft from an evidence note, append-only versions, Owner or role approve, list/read. Dedicated Beta file `catalog/sop_factory.sqlite` (created only on a successful draft; gitignored).
- `scripts/serve_beta.py` — `GET /api/sop`, `GET /api/sop/<id>`, `POST /api/sop/draft`, `POST /api/sop/version`, `POST /api/sop/approve` on `:8788`. Anonymous is 403. A person who is not Owner and does not already hold `core.sop.draft` / `core.sop.approve` / `core.sop.read` is 403. No permission row was inserted.
- `scripts/tests/test_sop_factory.py` — schema, refuse paths, approve gate, append-only triggers, CR bind, WIP four.

## Honesty (bound to the CR)

`CR-c4ed4e3fa9f15a40` is still OPEN, blocker `NEEDS_ENGINEERING`, next action the full loop (evidence → learn → approve → version → train → use). This slice is draft, version, and approve only. Training, acknowledgement, and operational use are not built, so the CR was not resolved and the ledger was not written.

- A draft `state` stays `DRAFT`. Live is derived from an approval row. A newer unapproved version does not replace the approved one.
- Client fields `live`, `proven`, `ready`, `maturity` are refused and write no row.
- An evidence note that is only a maturity word is refused.
- `CAP-CORE-11` ledger state stays SPECIFIED (ceiling BUILT; not already higher). Credits table unchanged. Ledger stays 77 rows. Score history unchanged.

## Preserved

WIP four digests unchanged and unstaged: `migrate_phase2_6_team_readiness.py`, `phase26_team.py`, `skills/__init__.py`, `wolf_intelligence.py`.

No Production (`:8787`). No Alchemist write. No staff grant. No score change.

## Prove

`python3 scripts/tests/test_sop_factory.py` → `PASS=109 FAIL=0`.

Live `:8788` `GET /api/sop` without a subject → 403. `:8787` still up.

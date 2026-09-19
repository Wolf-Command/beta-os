# CURSOR MISSION — CAP-INTEL-05 Approve-to-rule skeleton — 2026-09-20

**Decision served:** 2026-09-20 PICK, approve-to-rule learning loop skeleton on Beta only (`docs/deliveries/GROK-PLAN-INTEL-APPROVE-TO-RULE-V1-2026-09-19.md`). Lane `intel-approve-to-rule-v1`.

**Status:** skeleton is on Beta `:8788`. Honesty ceiling in code is **BUILT**. Not PROVEN. Not READY. Model C maturity not raised. `CAP-INTEL-05` stays **SPECIFIED**. `CR-be51980bd1194448` stays **OPEN** (`NEEDS_ENGINEERING`; next action `Approve-to-rule learning loop`).

## What landed

- `scripts/core/intel_approve_to_rule.py` — experiment note, then Owner or role approve, then a versioned rule stub. Three append-only tables. A stub is not executed and is not promoted. Dedicated Beta file `catalog/intel_approve_to_rule.sqlite` (created only on a successful note; gitignored). A read of a missing file does not create it.
- `scripts/serve_beta.py` — `GET /api/intel/approve-to-rule` and `GET /api/intel/approve-to-rule/{experiment_id}` on `:8788`. `POST /note`, `POST /approve`, `POST /rule`. Owner (`PERS-MATT`) or a role that `rbac.can` already grants. This slice does not insert a permission. Anonymous and staff are 403.
- `scripts/tests/test_intel_approve_to_rule.py` — loop, append-only, refusals, red-team table, CR bind, ceiling, WIP four.

Approve does not create a stub. A stub without an approval row is refused and writes nothing. A second stub is the next version. Neither version is promoted. `promoted` cannot be stored as 1.

## Honesty (bound to the CR)

`CR-be51980bd1194448` is still OPEN, blocker `NEEDS_ENGINEERING`, next action `Approve-to-rule learning loop`. This slice is the skeleton of that loop. It does not resolve the CR and does not write the ledger.

- `CAP-INTEL-05` ledger state stays SPECIFIED. The in-code ceiling is BUILT because the ledger is not already PROVEN or READY. `ceiling_for("PROVEN")` and `ceiling_for("READY")` report the existing word and write nothing back.
- `CAP-INTEL-01` stays BUILT. This slice is not that ledger.
- Credits table unchanged. Ledger stays 77 rows. Score history unchanged.

## Red team

| Case | Result |
| --- | --- |
| Invent PROVEN / READY | REFUSED — `score_refused`. Ledger not written. |
| Auto-promote | REFUSED — `promote_refused`. No production rule. Stub `promoted` stays 0. |
| Anon / staff | FAIL CLOSED — live anon `GET`, `POST /note`, and `POST /promote` are 403. Owner 200 proved on the test handler, not by a live Cloudflare session. |
| Write without approve | REFUSED — `approve_required`. No stub row. |

`PUT` on the rule path is 405 `writes_refused`. It cannot skip the note, approve, then stub steps.

## Owner prove path

`GET /api/intel/approve-to-rule` on `:8788`. Owner (`PERS-MATT`) only. The body names the gaps, the red-team table, and the ceiling. It does not create the sqlite file.

Steps, in order, Owner or an already-authorised role:

1. `POST /api/intel/approve-to-rule/note` with `experiment_note`.
2. `POST /api/intel/approve-to-rule/approve` with `note_id`.
3. `POST /api/intel/approve-to-rule/rule` with `note_id` and `rule_text`.

`POST /api/intel/approve-to-rule/promote` stays refused after a stub exists.

## Gaps still open

- A rule stub is not a live operating rule. Nothing is executed.
- Approval does not create a rule and does not promote one.
- Auto-promote to production rules is refused.
- Noise suppression and performance learning are not this slice.
- Chat agents are not this slice.
- The completion row is still OPEN. The ledger gap text is still the next action.
- No permission row was inserted. A staff seat without `intel.rule.note` or `intel.rule.approve` stays 403.

## Preserved

WIP four digests unchanged during the test run: `migrate_phase2_6_team_readiness.py`, `phase26_team.py`, `skills/__init__.py`, `wolf_intelligence.py`.

No Production (`:8787`). No Alchemist write. No score change.

## Prove

`python3 scripts/tests/test_intel_approve_to_rule.py` → `PASS=161 FAIL=0`.

Live after `launchctl kickstart -k gui/$(id -u)/net.wolfcommand.serve-beta` (Beta plist only):

- `:8787` listener pid stayed `20807`. `GET /api/health` → 200. Production process was not restarted.
- `:8788` restarted, listener pid `76097`.
- `curl http://127.0.0.1:8788/api/intel/approve-to-rule` → 403
- `POST /api/intel/approve-to-rule/note` → 403
- `POST /api/intel/approve-to-rule/promote` → 403
- Ledger `CAP-INTEL-05` first field remains `SPECIFIED`. `CAP-INTEL-01` remains `BUILT`. 77 rows.
- `CR-be51980bd1194448` remains `OPEN` / `NEEDS_ENGINEERING` / `Approve-to-rule learning loop`. Resolution evidence is null.
- `catalog/intel_approve_to_rule.sqlite` was not created by the anonymous calls.

Owner 200 on the live `:8788` process was not curled. Live mode is Cloudflare Access and this shell has no `Cf-Access-Jwt-Assertion`. The Owner 200 path was proved on the same `serve_beta` handler in the test, with `BETA_AUTH_MODE=development_assertion` and `X-Wolf-Subject: mrwolf@wolfcommand.net`.

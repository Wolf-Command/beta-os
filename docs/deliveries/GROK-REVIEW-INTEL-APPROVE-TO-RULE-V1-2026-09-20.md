# GROK REVIEW — CAP-INTEL-05 Approve-to-rule learning loop skeleton — 2026-09-20

## Verdict
**PASS**

## Scope check
- Working tree for this slice (baseline `f641a34` → completion commit):
  - `scripts/core/intel_approve_to_rule.py` (new)
  - `scripts/tests/test_intel_approve_to_rule.py` (new)
  - `scripts/serve_beta.py` (+approve-to-rule routes/handlers only; no unrelated hunks)
  - `scripts/wolf_intelligence.py` **not** in commit (WIP four; fortnight title helpers pre-exist dirty)
  - `docs/deliveries/GROK-PLAN-INTEL-APPROVE-TO-RULE-V1-2026-09-19.md`
  - `docs/deliveries/CURSOR-MISSION-INTEL-APPROVE-TO-RULE-V1-2026-09-20.md`
  - this review
  - `state/build-claims/2026-09-20.json` claim row `bf-intel-approve-to-rule-v1-20260920`
- WIP four not in commit (`migrate_phase2_6_team_readiness.py`, `phase26_team.py`, `skills/__init__.py`, `wolf_intelligence.py`). Digests locked by tests. No Alchemist write. No Model C ledger / score / credits edit.
- Class NEW CAPABILITY framework / skeleton (`beta-intelligence-foundation`). Experiment note → Owner/role approve → versioned append-only rule stub. No auto-promote. No live rule execution. No Production.
- `CAP-INTEL-05` stays **SPECIFIED**. In-code honesty ceiling **BUILT** only. Ledger 77 rows.
- CR `CR-be51980bd1194448` stays **OPEN** (`NEEDS_ENGINEERING`; next action Approve-to-rule learning loop). Do not false-resolve.

## Prove
- `python3 scripts/tests/test_intel_approve_to_rule.py` → **PASS=161 FAIL=0** (re-run 2026-09-20 ~02:42 WITA)
- CAP-INTEL-05 ledger first field **SPECIFIED**; assessments len **77**
- CR `CR-be51980bd1194448` **OPEN** / **NEEDS_ENGINEERING** / next action unchanged; resolution_evidence null
- Live `:8788` anon `GET /api/intel/approve-to-rule` → **403** `missing_auth`; `POST /note` → **403**; `POST /promote` → **403**
- Production `:8787` still listening; Beta `:8788` listening
- Owner 200 proved on test handler under `BETA_AUTH_MODE=development_assertion` (no Cf-Access JWT in this shell)
- Cursor log: `EXIT: SUCCESS` / `CURSOR_DONE` / shell exit 0

## Red team
| Attack | Result |
| --- | --- |
| Invent PROVEN / READY | PASS — `score_refused`; CAP-INTEL-05 stays SPECIFIED; ledger not written |
| Auto-promote | PASS — `promote_refused`; stub `promoted` stays 0 |
| Anon / staff open | PASS — live anon GET/POST 403; Owner/role gate |
| Write stub without approve | PASS — `approve_required`; no stub row |
| PUT skip steps | PASS — 405 `writes_refused` |
| Resolve CR without product exit | PASS — CR stays OPEN; no resolution_evidence |
| Touch WIP four | PASS — digests green; not part of this lane commit |
| Production :8787 mutate | PASS — Beta routes only; :8787 still up |
| Write ledger / score history / credits | PASS — unchanged; 77 rows |
| Alchemist / money path | PASS — out of bound |
| Raise maturity via skeleton | PASS — honesty ceiling BUILT; CAP stays SPECIFIED |

## Findings
- None in-scope FAIL. Work product matches plan refuse rules.
- Factory note: lane-only commit is Peaches orchestration after Cursor left work uncommitted; WIP four and unrelated dirty trees excluded.
- Live Owner 200 not curled (Cloudflare Access). Same handler proved in tests.

## Completion Register
Do not false-resolve `CR-be51980bd1194448`. Delivery evidence is the completion commit + test PASS + anon 403 prove. CR remains OPEN for the real learning loop beyond skeleton.

## Close action
Mark lane `intel-approve-to-rule-v1` COMPLETED, clear ACTIVE, `close_slice` → drain wave-5 then arm next eligible safe wave (61 OPEN eng-debt remains; IDLE with eligible queue is a factory defect).

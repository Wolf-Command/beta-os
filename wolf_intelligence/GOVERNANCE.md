# WI Capacity Governance

Peaches (Grok Bot, `grok_bot_sub`) capacity is **protected capacity**. Substantive work defaults to
specialised subscription workers; Grok is reserved for orchestration, owner conversation, and
exception handling unless a valid reason code applies.

## Config (versioned in git)

| File | Purpose |
|------|---------|
| `config/governance/worker-allocation-policy.json` | Rules, thresholds, reason codes, protected classes |
| `config/governance/worker-allocation-policy.schema.json` | Schema + invariant pins (`metered_fallback: NEVER`, `paid_spend: OFF`) |
| `config/governance/capacity-observed.json` | Seed capacity observations |

Override policy path for tests: `WOLF_INTELLIGENCE_GOVERNANCE_POLICY`.

## Runtime state (`$WOLF_INTELLIGENCE_STATE_ROOT/governance/`)

- `audit.jsonl` — policy fail-closed and routing imbalance events
- `dispatch-ledger.jsonl` — every allocation decision
- `capacity-observations.jsonl` — append-only owner/API observations
- `tightening.json` — persisted `grok_routing_penalty`

## Capacity states

`NORMAL` → `CONSERVE` → `RESERVE` → `EXHAUSTED` (monotonic; decay never improves state).

Grok thresholds: conserve 30%, reserve 60%, exhausted 95%. Others: 70 / 85 / 100.

## Grok reason codes (substantive work only)

- `BENCHMARK_SELECTED` — Grok in top quality tie band (verified from `routing-policy-real.json`)
- `REQUIRES_GROK_ENVIRONMENT` — requires justification text
- `OTHERS_UNAVAILABLE` — verified: no other eligible worker
- `EXPLICIT_JUSTIFIED` — requires justification text (min length in policy)

Protected classes need no code. Invalid/missing codes → `GROK_JUSTIFICATION_INVALID`.

## CLI

```bash
python3 -m wolf_intelligence governance status
python3 -m wolf_intelligence governance decide --task-class coding [--id ID] [--grok-reason CODE] [--justification T] [--now ISO]
```

## Owner UI

```bash
WOLF_INTELLIGENCE_UI_TOKEN=... python3 -m wolf_intelligence serve-ui
```

- `GET /api/governance/status` (token required)
- `POST /api/governance/decide` (token required, body = work item JSON)

Port: `WOLF_INTELLIGENCE_UI_PORT` (default 8799; refuses 8787 and 8788).

## Tests

```bash
python3 -m unittest discover -s wolf_intelligence/tests -v
```

Governance tests: `tests/test_capacity_governance.py` (offline; sets temp `WOLF_INTELLIGENCE_STATE_ROOT`).

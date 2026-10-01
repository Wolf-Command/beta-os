# ATRIUM-OPS-SECURITY-EVIDENCE-1 — Security / CCTV evidence workflow

Eng proof only. `staff_ready` stays false. Not HUMAN_PROVEN. Not a CCTV viewer. No stream invented. Prod `:8787` health-checked only (not restarted, not written).

Decision served: 2026-10-02 PICK ATRIUM-OPS-SECURITY-EVIDENCE-1 in `~/.openclaw/wolf-output/decisions.md` (Owner order ATRIUM-OPS-FOUR-20261002).

## Job built

Deterministic workflow on Beta:

incident → time/location → people/asset → evidence reference → optional CCTV timestamp/camera ref → responsible → severity/escalation → action → follow-up → closure → immutable audit/evidence log.

Categories mapped from Interview R1/R2/R8 + V1: `cash_theft`, `anti_theft`, `access`, `injury`, `slip`, `cut`, `medical`, `fire`, `damage`, `security`, `other`.

## Data

- Beta sqlite: `state/security-evidence/security_evidence.sqlite`
- Tables: `security_incidents` (mutable status/fields), `security_evidence` (append-only triggers), `security_audit` (append-only triggers)
- V1 seed: read-only open of `~/.openclaw/workspace/wolf-system/state/incidents.db`; imported row id=1 near-miss slip with provenance `v1:incidents.db#id=1`; V1 mtime unchanged
- CCTV: `cctv_stream=false`, status `EXTERNAL_UNAVAILABLE`; timestamp + camera ref are text fields only

## Live HTTP on `:8788` (after Beta kickstart)

| Path | Result |
|---|---|
| `GET /api/msc/security-evidence` | 200, register_state PARTIAL, V1 seed imported 1, staff_ready false |
| `GET /msc/security-evidence` | 200 desk HTML |
| `POST /api/msc/security-evidence` | 200 create `SEC-3BA1CE4F0733` |
| `POST …/{id}/evidence` | 200 → investigating |
| `POST …/{id}/escalate` | 200 → escalated / critical |
| `POST …/{id}/close` | 200 → closed |
| `POST …/stream` | 405 `cctv_stream_unavailable` |
| `GET :8788 /api/health` | 200 |
| `GET :8787 /api/health` | 200 (read only) |

## Tests

`scripts/tests/test_atrium_ops_security_evidence_1.py`: 43 passed, 0 failed (temp DB + in-process Beta + wiring checks).

## Register

`need.security`: MISSING → PARTIAL (real workflow rows + API + desk). `staff_ready` remains false until human commission.

## Left undone

Human commission. Live CCTV integration (explicitly out of scope — EXTERNAL). Camera inventory. Staff training / operating adoption.

## Forbidden preserved

No CCTV live view. No invented footage. No prod `:8787` mutate. No Intelligence phase / Exit Report. Honesty-only board was not counted as done.

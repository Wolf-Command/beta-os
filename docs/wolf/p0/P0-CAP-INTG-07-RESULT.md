# P0 CAP-INTG-07 — Secrets & Environment Separation — 27 Sep 2026

Pack S2. Beta/local only. Production `:8787` stayed pid 15975 (`serve.py`). Beta `:8788` stayed pid 59914 (`scripts/serve_beta.py`). No restart. No money, bank, payment, ESB, or NAS write. No secret value was read into this note. No second vault was built. No Access include changed. No push.

TECHNICAL PROOF is the search plus the two suites. DEPLOYED ROUTE PROOF is the unsigned Beta status below. No route was added. STAFF READINESS stays no. HUMAN COMMISSIONING stays no. OPERATING ADOPTION stays not measured. SYSTEM stays 19.65 / 77 = 25.52%.

## BEFORE

SYSTEM SPECIFIED (0.05). The 2026-09-18 owner audit rejected PROVEN. `.env.example`, `.gitignore`, and `test_cap_intg_07_environment_separation.py` were on record as hygiene, not a vault prove. The Beta skeleton in `scripts/core/intg_secrets_env.py` names empty vault, rotation, and Beta-Production slots. `catalog/intg_secrets_env.sqlite` was absent. No search of the live stores was in the queue.

## AFTER

The search named one authorised credential directory and no vault product.

The directory is `~/.openclaw/credentials/`. Decision 2026-07-21 calls it the system of record and says 1Password is dead. `INDEX.md` in that directory says the same. This session counted 37 files, 30 of them JSON. Values were not opened. A filename in that directory contains the word production. That is not Dev, Beta, and Production separation.

`op` 2.35.0 is installed. `op account list` exited 0 with no account lines. `op whoami` exited 1, no account. `op vault list` exited 1. The 1Password application is absent. `~/.config/op` holds an empty socket and nothing else.

The keychain service `wolf-secrets-vault` exists. Its dates are 2026-08-09. It is the passphrase slot for `secrets-offsite.py`, which writes encrypted copies under `~/.openclaw/secrets-vault/`. Eight copy names are present, the latest dated 20260927. The passphrase was not printed. Those copies are not a vault product, not a rotation prove, and not environment separation.

Absent: HashiCorp Vault, Doppler, Infisical, SOPS, age, pass, Bitwarden. No `.vault-token`.

Not this capability: footage crypt inside `~/.openclaw/wolf-secrets.env` (54 names, values not printed), rclone remotes, and the Atrium scratch backup. LaunchAgents whose labels contain `vault-` are knowledge feeds or a file mirror. `com.wolfcommand.secrets-offsite` runs the copy script above.

The Beta skeleton was left empty. No slot was filled.

## EVIDENCE

Commit `44cd296`.

Ledger file `state/model-c-baseline-assessments.json` was not edited. SHA256 `852f267a4bc71fe86f8972d077ec1c83f93a2de64735a2b2c8713488ddea3305`. `CAP-INTG-07` is still `SPECIFIED`. Row count 77. Score was not raised. `staff_ready` and `human_commissioned` stay false. Completion row `CR-273f30371bd52c8a` was not resolved.

```
WOLF_TEST_MODE=1 python3 scripts/tests/test_cap_intg_07_environment_separation.py
CAP-INTG-07 RESULT: PASS=12 FAIL=0
```

That suite is the repo-check. It does not close this item.

```
WOLF_TEST_MODE=1 python3 scripts/tests/test_intg_secrets_env.py
PASS=167 FAIL=0
```

The suite's own line was `ledger file still unchanged at exit`.

Listeners, unchanged:

```
Python  15975  127.0.0.1:8787  serve.py
Python  59914  127.0.0.1:8788  scripts/serve_beta.py
```

Origin `http://127.0.0.1:8788` on pid 59914:

| request | status |
| --- | --- |
| `GET /api/intg/secrets` | 403 |
| `GET /intg-secrets` | 403 |
| `GET /api/health` | 200 |

## FINAL STATE

BLOCKED_OWNER.

The authorised store is a plaintext directory. No vault product is signed in or named for this capability. Matt has to name that product before a rotation or Dev/Beta/Prod prove can exist. Cursor does not build a second vault. The ledger stays SPECIFIED.

## HUMAN NEXT

Matt names the vault product for Dev, Beta, and Production, or writes down that none is authorised. There is no one-minute staff walk for this row. Do not mark anyone commissioned from this file.

RESULT: PASS

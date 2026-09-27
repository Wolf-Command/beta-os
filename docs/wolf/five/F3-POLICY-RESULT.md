# F3 — Proposed policies and credential discovery — 28 Sep 2026

Pack F3 of the five-pack sprint. Owner brief 28 Sep 2026 06:46 WITA, item 3, and the credential rule at 06:48 WITA. Extends Wolf Core. This is not a new system. Beta/local only. Production `:8787` stayed pid 15975 (`serve.py`). Beta `:8788` was restarted from pid 22379 to pid 25471 (`scripts/serve_beta.py`) so the war-room classification is the process that serves the route. It came back on `:8788`. No money, bank, payment, ESB, or NAS write. No policy row, SoD row, authority limit, variance row, grant, or person was inserted. No secret value is in this note. No push. Grok was not called.

TECHNICAL PROOF is the read-only catalog counts, the war-room suite, and the CAP-INTG-07 repo-check, all through `scripts/tests/run_guarded.py` where they are tests. DEPLOYED ROUTE PROOF is unsigned 403 on the war-room and approvals routes on pid 25471, honesty still reporting no variance policy, and the public hostname redirecting `/api/core/approvals` to the Access login. A seated 200 was not observed. STAFF READINESS stays no. HUMAN COMMISSIONING stays no. OPERATING ADOPTION stays not measured. SYSTEM stays 19.65 / 77 = 25.52%. The ledger file was not edited.

## Policies

Three proposals, each with an APPROVE / CHANGE page:

- `docs/wolf/five/PROPOSED-FINANCE-CONTROL-MATRIX.md`
- `docs/wolf/five/PROPOSED-WIDE-APPROVAL-POLICY.md`
- `docs/wolf/five/PROPOSED-UMA-VARIANCE-POLICY.md`

They were not loaded. `INACTIVE` exists on governance policies, SoD constraints, authority limits, and variance policies, and evaluate reads `ACTIVE` only. Authority-limit amounts and variance amounts cannot be stored without a number. The green SoD and authority-limit suites require those live counts to stay 0. An unresolved threshold was not invented to fill the column. Live counts after the pack: governance policies 1 (`GPO-HABITAT-CONTENT-PUBLISH`, ACTIVE, already there), SoD constraints 0, authority limits 0, variance policies 0.

`CAP-CORE-07` stays BLOCKED_OWNER until Matt marks the wide-policy page. `CAP-CORE-08` stays BLOCKED_OWNER until Matt marks the finance matrix. The Uma closer seat stays empty. That is a separate human decision. Honesty on pid 25471: `variance_policy_display` BLOCKED BY BUSINESS POLICY, `live_variance_threshold` 0 (the row count), `live_monetary_authority` 0, closer WAITING FOR VERIFIED CLOSING OPERATOR, settlement UNAVAILABLE.

## Credentials

`docs/wolf/five/CREDENTIAL-DISCOVERY.md` and `docs/wolf/five/VAULT-FINDING.md`.

The working secret mechanism is `~/.openclaw/credentials/` (37 files, 30 JSON) and `~/.openclaw/wolf-secrets.env`. Keychain service `wolf-secrets-vault` is the passphrase for encrypted copies under `~/.openclaw/secrets-vault/`. 1Password has no account. No second vault was built. No owner product decision remains. Keep that mechanism.

`CAP-INTG-07` moved from BLOCKED_OWNER to OPEN. Classification: CURSOR CAN CLOSE the separation prove. Credential ask: none. The war-room owner-decision set no longer includes it. Priority stays P0. Ledger stays SPECIFIED. Work classes on the built room are `cursor_build`, `local_deterministic`, and `human_commissioning`. `owner_decision` is absent. The `human_commissioning` class is the war room's generic class for a row that is not READY. It is not a commissioning record.

The only remaining credential ask is Yanolja: `api_key` in the existing `yanolja.json` is empty. Do not paste a key in chat. `CAP-INTG-01` stays WAITING_EXTERNAL. B2 list, the ESB warehouse read, the bank-archive count, and the NAS mounts were harmless reads. Cloudflare R2 list returned 403. That is not a request for a broader token. Gmail, Drive, Calendar, Klaviyo, Metricool, the ESB API, and SMTP were not called.

## Suites

No repair. Both through `scripts/tests/run_guarded.py`.

| suite | result |
| --- | --- |
| `test_completion_war_room.py` | PASS=227 FAIL=0 |
| `test_cap_intg_07_environment_separation.py` | PASS=12 FAIL=0 |

The war-room suite logged `audit.safe_record failed: test process refuses canonical Beta write`. The suite still exited 0 and recorded the ledger unchanged. Those lines are the F1 guard. They are not a failed assertion.

Listeners after the restart: pid 15975 is still `serve.py` on `:8787`. pid 25471 is `scripts/serve_beta.py` on `:8788`. `GET /api/health` on `:8788` is 200. Unsigned `GET /api/owner/war-room` and `GET /api/core/approvals` are 403. On `https://beta.wolfcommand.net`, `GET /api/core/approvals` is 302 to the Access login, `server: cloudflare`, `www-authenticate` starting `Cloudflare-Access`. The login query string was not recorded.

RESULT: PASS

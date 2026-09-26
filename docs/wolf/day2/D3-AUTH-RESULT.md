# D3 — Cloudflare Beta sign-in path — 27 Sep 2026

DEPLOYED ROUTE PROOF only. Not staff readiness. Not human commissioning. Not operating adoption.

Beta/local only. Production `:8787` stayed pid 15975 (`serve.py`). Beta `:8788` stayed pid 4443 (`scripts/serve_beta.py`). It was not restarted. No people were created. No assignments were written. Human commissioned: no.

## BEFORE

Beta `:8788` was already `cloudflare_access` with `development_assertion_allowed` false. Unsigned routes returned 403. No completion register existed for this pack. `state/commissioning/cf-sim-public.jwk.json` was absent, so the live verifier had no local public-key bypass.

Representative seats asked for: Creative Director, BZG F&B Operations Lead, venue closer, finance (external accountant / controller), Owner.

## DONE

Documented the live path. Counted existing Wolf Core seats. Hit the deployed origin and the public Access hostname. Ran the existing verifier suite. Wrote `state/completion-register/DEPLOYED-ROUTE-PROOF-20260927.json`. No application code change. No repair pass.

### Exact path

1. `GET /api/core/auth-mode` on the running process reads `core.request_auth.auth_mode()`. Unset `BETA_AUTH_MODE` is `cloudflare_access`. `development_assertion` is used only when that env var is exactly `development_assertion`.
2. A protected route calls `Handler._resolve_identity` → `request_auth.resolve_request_identity`.
3. Header read is `Cf-Access-Jwt-Assertion` only (`cf_access.token_from_headers`). `Cf-Access-Authenticated-User-Email` is named `UNTRUSTED_EMAIL_HEADER` and is not proof. `X-Wolf-Subject`, JSON `subject` / `actor`, and query `subject` are ignored in this mode.
4. `cf_access.verify_access_jwt` requires RS256, a JWKS key from `BETA_CF_ACCESS_TEAM_DOMAIN` (default `https://wolfcommand.cloudflareaccess.com`) at `/cdn-cgi/access/certs`, `iss` equal to that domain, `aud` equal to `BETA_CF_ACCESS_AUD`, `exp` in the future, `iat` not more than 30 seconds ahead, and an email claim (`email`, `identity`, or `custom.email`). The token is not logged.
5. The email is bound by `identity.resolve_verified_person`: `org_auth_identities.provider` in (`email`, `cloudflare`), identifier match, identity `ACTIVE`, person `ACTIVE`. Unknown emails return `unknown_identity`. No person is auto-created.
6. The bound `person_id` is the actor. Assignments are `org_assignments` joined to `org_positions.role_id`, status `ACTIVE`, `end_at` null. Route gates then differ:
   - `/bzg/uma-blu` and `/api/bzg/uma-blu/*`: identity plus `venue.close.read` on `ENT-BZG` / `BZG-UMA`, plus `SCOPE-BZG-UMA` or `SCOPE-BZG-FB`.
   - `/wolf` and `/owner-empire-pack`: identity, `person_id` must be `PERS-MATT`, plus `progress.read`.
   - `/ggv/finance` and `/api/ggv/finance`: identity plus `finance.nota.read` on the finance target. A person whose only active role is `ROLE-GGV-EXTERNAL-ACCOUNTANT` is also walled off every other path.
   - `/content-2.0`: shell `filter_hrefs` after a quiet identity resolve. A failed resolve is rendered as anonymous `forbidden`, including a bad JWT.
   - `/my-work`: any failed resolve is `Sign in required.`

There is no `ROLE-OWNER` row. Owner in the catalog is `ROLE-MATT`. Chrome `build_whoami` adds the label `ROLE-OWNER` for the OWNER audience. That label is not a seat.

### Seats (existing rows only)

| Role asked | Catalog role | Seat | Authorised email |
| --- | --- | --- | --- |
| Creative Director | `ROLE-GGV-CREATIVE-DIRECTOR` | `PERS-HAIKAL` / `ASG-HAIKAL-CD-1` / `POS-GGV-CREATIVE-DIRECTOR-1` | yes, `haikalqilbari123@gmail.com` |
| BZG F&B Operations Lead | `ROLE-BZG-FB-OPS-LEAD` | `PERS-DEVI` / `ASG-DEVI-FB-OPS-1` / `POS-BZG-FB-OPS-1` | yes, `deviputu236@gmail.com` |
| Venue closer | `ROLE-BZG-CLOSER` | none. Position `POS-BZG-CLOSER-UMA-1` exists, label `Closing Operator · Uma Blu (WAITING roster)`. Active assignments: 0 | no person |
| Finance, external accountant | `ROLE-GGV-EXTERNAL-ACCOUNTANT` | none. Position `POS-GGV-EXT-ACCT` exists. Active assignments: 0 | no person |
| Finance, controller | no role whose id or name contains `control` | none | no person |
| Owner | `ROLE-MATT` (`Owner / Executive`) | `PERS-MATT` / `ASG-MATT-OWNER-1` (primary) and `ASG-INTEL-OPERATOR-MATT` | yes, `mrwolf@wolfcommand.net` |

`PERS-AMANDA` is seated as `ROLE-CONTENT-MGMT`, not as accountant or controller. Her role grant includes `finance.nota.read`. That is not an accountant seat.

`PERS-LEAD-DEMO` has no auth identity and is not one of these roles.

### What was proven on the deployed route

Origin `http://127.0.0.1:8788` (pid 4443):

| Route | No header | `X-Wolf-Subject` or email header | `Cf-Access-Jwt-Assertion: a.b.c` |
| --- | --- | --- | --- |
| `/bzg/uma-blu` | 403 `missing_auth` | 403 `missing_auth` | 403 `invalid_token` |
| `/wolf` | 403 `missing_auth` | 403 `missing_auth` | 403 `invalid_token` |
| `/ggv/finance` | 403 `missing_auth` | 403 `missing_auth` | 403 `invalid_token` |
| `/api/core/me` | 403 `missing_auth` | 403 `missing_auth` | 403 `invalid_token` |
| `/api/bzg/uma-blu/today`, `/api/ggv/finance`, `/api/owner/empire-pack` | 403 `missing_auth` | — | — |
| `/content-2.0` | 403 `forbidden` (not in scope) | same | same (bad JWT is not echoed as `invalid_token`) |
| `/my-work` | 403 `Sign in required.` | same | same |

Public `https://beta.wolfcommand.net` for `/`, `/content-2.0`, `/bzg/uma-blu`, `/wolf`, `/ggv/finance`, `/my-work`, and `/not-a-real-route`: each returned HTTP 302 to `https://wolfcommand.cloudflareaccess.com/cdn-cgi/access/login/beta.wolfcommand.net`, `server: cloudflare`, `www-authenticate: Cloudflare-Access`. The nonsense path did the same, so this proves the Access gate in front of the hostname. It does not prove which origin route would answer after login.

Live JWKS `https://wolfcommand.cloudflareaccess.com/cdn-cgi/access/certs` returned HTTP 200, 2 RS256 keys. Key material was not recorded.

No seated role returned HTTP 200. No cross-role denial under a verified person was observed on `:8788`. Those need a real Cloudflare login.

### What the local verifier showed (not sufficient alone)

`python3 scripts/tests/test_real_auth_binding.py` exited 0, `SUMMARY pass=44 fail=0`. It signs with an ephemeral key and a stubbed JWKS inside the test process. It does not present a Cloudflare token to pid 4443. The suite's own header says a live Cloudflare token is not required for that file.

Same functions, read-only, after `resolve_verified_person` on the catalog (projection, not an HTTP call to `:8788`):

| Person | Landing the shell would choose | `/content-2.0` in shell hrefs | `venue.close.read` on Uma | `finance.nota.read` | `progress.read` | Owner page (`PERS-MATT` only) |
| --- | --- | --- | --- | --- | --- | --- |
| `PERS-HAIKAL` | `/content-2.0` | yes | no | no | no | no |
| `PERS-DEVI` | `/bzg/uma-blu` | no | yes | no | no | no |
| `PERS-MATT` | `/wolf` | yes | yes | yes | yes | yes |
| `PERS-AMANDA` | `/ggv-ops-pack` (content management, not this pack's finance seat) | no | no | yes | no | no |

## VERIFIED

Production and Beta listeners after the checks:

```
Python  15975  127.0.0.1:8787  serve.py
Python  4443   127.0.0.1:8788  scripts/serve_beta.py
```

```
curl -sS http://127.0.0.1:8788/api/core/auth-mode
{"ok": true, "auth_mode": "cloudflare_access", "development_assertion_allowed": false, "cloudflare_aud_configured": true, "team_domain": "https://wolfcommand.cloudflareaccess.com", "identity_assurance_default": "none", ...}
```

`BETA_CF_ACCESS_AUD` is set on that process. The value was not printed.

Unsigned and spoofed probes (status and error only):

```
403 missing_auth   /bzg/uma-blu  /wolf  /ggv/finance  /api/core/me
403 invalid_token  same four routes with Cf-Access-Jwt-Assertion: a.b.c
403 forbidden      /content-2.0  (missing, subject, email header, and a.b.c)
403 Sign in required.  /my-work  (same four header cases)
```

Public Access, one line of the set (cookie values omitted). The other six paths matched this status and login host:

```
HTTP/2 302
location_host https wolfcommand.cloudflareaccess.com path /cdn-cgi/access/login/beta.wolfcommand.net
www-authenticate: Cloudflare-Access
server: cloudflare
```

JWKS:

```
jwks_http 200
key_count 2
algs ['RS256', 'RS256']
```

Verifier suite:

```
python3 scripts/tests/test_real_auth_binding.py
SUMMARY pass=44 fail=0
```

The suite logged `ensure_schema` against the live catalog and reported migrations already applied. After it, active `ROLE-BZG-CLOSER` assignments were still 0 and active `ROLE-GGV-EXTERNAL-ACCOUNTANT` assignments were still 0. Listeners were still pid 15975 and pid 4443.

Seat projection (read-only catalog, not HTTP):

```
PERS-HAIKAL bound_ok True landing /content-2.0 venue.close.read False finance.nota.read False
PERS-DEVI   bound_ok True landing /bzg/uma-blu venue.close.read True  finance.nota.read False
PERS-MATT   bound_ok True landing /wolf        venue.close.read True  finance.nota.read True progress.read True
CLOSER_ASSIGN 0
ACCT_ASSIGN 0
CONTROLLER_ROLES []
ROLE_OWNER_ROW 0
```

## WAITING HUMAN

- Seat decision: who, if anyone, is assigned to `ROLE-BZG-CLOSER` / `POS-BZG-CLOSER-UMA-1`. No person was created here.
- Seat decision: who, if anyone, is assigned to `ROLE-GGV-EXTERNAL-ACCOUNTANT` / `POS-GGV-EXT-ACCT`. No controller role exists to seat.
- A person with a Cloudflare Access login opens `https://beta.wolfcommand.net` and reaches the origin as that email. This session had no Access session, so the allow path was not walked. That walk is still not human commissioning and not operating adoption.

## BLOCKERS

The deployed allow path for the three seated people was not observed. A locally signed JWT from `test_real_auth_binding.py` does not satisfy it. The public hostname stops at Cloudflare Access before the origin, including on a nonsense path.

`/content-2.0` and `/my-work` on pid 4443 collapse a bad JWT into the anonymous 403. Cryptographic `invalid_token` was observed on `/bzg/uma-blu`, `/wolf`, `/ggv/finance`, and `/api/core/me` on that same process.

## NEXT HUMAN TEST

Sign in through Cloudflare Access on `https://beta.wolfcommand.net`. Do not send `X-Wolf-Subject`. Do not mark anyone commissioned.

1. Haikal (`haikalqilbari123@gmail.com`). Expect `/content-2.0` in scope. Expect 403 on `/bzg/uma-blu`, `/wolf`, and `/ggv/finance`.
2. Devi (`deviputu236@gmail.com`). Expect `/bzg/uma-blu` to open. Expect 403 on `/content-2.0`, `/wolf`, and `/ggv/finance`.
3. Matthew Goss (`mrwolf@wolfcommand.net`). Expect `/wolf` to open. `/ggv/finance` is allowed by `finance.nota.read` on `ROLE-MATT`. `/bzg/uma-blu` is allowed by `venue.close.read` plus Uma scope. Record the statuses. This is still not commissioning.
4. Leave the closer and the external accountant unseated until a person is chosen. Amanda is content management. A finance page for her would be that grant, not an accountant seat.

RESULT: FAIL

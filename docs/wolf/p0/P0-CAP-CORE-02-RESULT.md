# P0 CAP-CORE-02 — Person & Auth Identity — 27 Sep 2026

Pack S2. Beta/local only. Production `:8787` stayed pid 15975 (`serve.py`). Beta `:8788` was restarted from pid 58953 to pid 59914 (`scripts/serve_beta.py`) so the new route loaded. No money, bank, payment, ESB, or NAS write. No person created. No assignment written. No JWT minted for the live origin. No Access include changed. No push.

TECHNICAL PROOF is the suite and the origin redirect. DEPLOYED ROUTE PROOF is the live `:8788` status below, plus the public Access logout clearing the authorization cookie. STAFF READINESS stays no. HUMAN COMMISSIONING stays no. OPERATING ADOPTION stays not measured. SYSTEM stays 19.65 / 77 = 25.52%.

## BEFORE

SYSTEM READY (1.00). Staff ready no. Human commissioned no. `test_real_auth_binding.py` was PASS=44. Unsigned and a bad JWT were 403 on Beta. No seated 200 had been observed. The shell linked to `/signout`. `GET /signout` on Beta `:8788` pid 58953 was HTTP 404.

## AFTER

`GET /signout` and `GET /signout/` on the origin return 302 to `https://beta.wolfcommand.net/cdn-cgi/access/logout`. The origin sets no cookie. A `next` query, `X-Wolf-Subject`, and `Cf-Access-Authenticated-User-Email` do not change the location. A bad JWT on `/signout` is still that logout, not an allow. `/api/core/auth-mode` reports the same logout URL and does not print the audience.

The public logout is Cloudflare's application logout. It sets `CF_Authorization`, `CF_Binding`, `CF_Device`, and `CF_Session` to `deleted` with `Expires` in 1970. That is the cookie clear. The next request on the public host without that cookie is the Access login redirect, which this session observed on unsigned `/signout` and `/api/core/me`.

A seated session was not observed. Cursor did not sign in as Haikal, Devi, or Matt.

## EVIDENCE

Commit `8247252`. Route code: `scripts/serve_beta.py`, `scripts/core/request_auth.py`. Suite: `scripts/tests/test_real_auth_binding.py`.

```
WOLF_TEST_MODE=1 python3 scripts/tests/test_real_auth_binding.py
SUMMARY pass=51 fail=0
```

Previously green suites, this session, exit 0:

| suite | result |
| --- | --- |
| `test_dashboard_truth.py` | PASS=62 FAIL=0 |
| `test_owner_command.py` | PASS=66 FAIL=0 |
| `test_business_dashboard.py` | PASS=131 FAIL=0 |
| `test_role_dashboard.py` | PASS=144 FAIL=0 |
| `test_completion_war_room.py` | PASS=227 FAIL=0 |
| `test_lead_spine.py` | PASS=33 FAIL=0 |
| `test_haikal_content_ux_wave1.py` | PASS=21 FAIL=0 |

Listeners after the Beta restart:

```
Python  15975  127.0.0.1:8787  serve.py
Python  59914  127.0.0.1:8788  scripts/serve_beta.py
```

Origin `http://127.0.0.1:8788` on pid 59914:

| request | status |
| --- | --- |
| `GET /signout` | 302 `https://beta.wolfcommand.net/cdn-cgi/access/logout`, no Set-Cookie |
| `GET /signout/` | 302 same location |
| `GET /signout?next=https://evil.example/phish` with subject and email headers | 302 same location |
| `GET /api/core/me` | 403 `missing_auth` |
| `GET /api/core/me` with `Cf-Access-Jwt-Assertion: a.b.c` | 403 `invalid_token` |
| `GET /api/core/me` with `X-Wolf-Subject` | 403 `missing_auth` |
| `GET /api/core/auth-mode` | 200 `auth_mode=cloudflare_access`, `access_logout_url` matches the redirect, audience value not printed |
| `GET /api/health` | 200 |

Public `https://beta.wolfcommand.net` with no session:

| request | status |
| --- | --- |
| `GET /cdn-cgi/access/logout` | 200 `server: cloudflare`. Authorization cookies set to `deleted`, expired 1970 |
| `GET /signout` | 302 to `https://wolfcommand.cloudflareaccess.com/cdn-cgi/access/login/beta.wolfcommand.net`, `www-authenticate: Cloudflare-Access` |
| `GET /api/core/me` | 302 to the same login |

The unsigned public `/signout` stops at Access because the whole hostname is gated. A signed-in browser is the request that reaches the origin redirect. That hop was not walked.

`state/model-c-baseline-assessments.json` was not edited. It stays byte-identical to the W3-P5 backup, and CAP-CORE-02 stays READY. Score was not raised. The sign-out fact is on the commissioning register and the gap register. `staff_ready` and `human_commissioned` stay false in `state/completion-register/COMMISSIONING-STATE-20260927.json` and `GAP-REGISTER-20260927.json`.

## FINAL STATE

READY_FOR_HUMAN.

The sign-out route is deployed. The three seated sign-ins, the cross-role refusals, and the refusal after Sign out are the remaining human walk. That walk is not done.

## HUMAN NEXT

One minute, in `docs/wolf/p0/HUMAN-TESTS.md`. On https://beta.wolfcommand.net, Haikal, Devi, and Matt each sign in, check the pages named there, click Sign out, and confirm the page they just used asks them to sign in again. Write down the statuses. Do not mark anyone commissioned from this file.

RESULT: PASS

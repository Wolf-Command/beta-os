# ZAYENFIX-1 — role routing repair

Decision served: owner brief 28 Sep 2026 staff access (extends the same seat; no new system). Beta `:8788` only. Production `:8787` was not restarted. No Cloudflare edit. No grant was added. `staff_ready` and `human_commissioned` stay false.

## Human fail

Zayen (`laluzayen@gmail.com`) signed in to https://beta.wolfcommand.net on 28 Sep 2026 at 13:18 WITA and saw raw JSON:

```json
{"error":"forbidden","message":"This account is limited to Atrium Finance."}
```

She should have landed on Atrium Finance. Retest is PENDING. The commissioning row stays PENDING/FAIL until she writes the next result.

## Root cause

Confirmed in code and in `scripts/tests/test_role_routing_20260928.py`.

`officer_must_deny()` in `scripts/core/staff_access.py` returns true for Zayen on `/`. Her only active role is `ROLE-AMG-FINANCE-OFFICER`. `/` is not in `ATRIUM_PAGE_PATHS` or `ATRIUM_CHROME_PATHS`.

`BetaHandler._atrium_finance_wall()` in `scripts/serve_beta.py` runs near the start of `do_GET`, before any landing redirect. On that deny it called `_send_json` with HTTP 403. A browser navigation to `/` therefore received raw JSON. The same wall caught GGV Finance, Uma Blu, Owner, and staff admin before those pages could render.

The function still denies `/`. The handler now redirects a signed-in `/` before the wall runs.

## Fix

Signed-in `GET /` and `GET /index.html` return 302 to the human page of the active primary assignment. Chain: AuthIdentity → Person → active primary Assignment → that role's page. Refresh of the destination stays on that page (200). After sign-out, the next signed-in request to `/` is the same 302. A deep link to the person's own page stays on that page. A deep link to a forbidden page stays denied.

A browser page request (`Accept` contains `text/html`, path is not `/api/`) that is denied returns an HTML Access Denied page: who is signed in, a plain sentence, and a button back to that person's workspace. `/api/*` stays JSON 403, including when the browser sends `text/html`. A script `Accept: */*` on a page still gets JSON 403, so the existing probes stay on status and body.

Zayen's grants are unchanged: atrium read, journal draft, `approval.request` on Atrium. No pay, bank, owner, admin, GGV, or Blu Zone grant was added.

Amanda's content page follows her primary Content Management assignment. The chrome audience map is unchanged. The content HTML gate also allows the page when an active assignment's human page is `/content-2.0`. That is the seat she already has. It is not a new permission.

## Page Zayen should open

https://beta.wolfcommand.net/amg/finance

That route serves `dashboards/amg-finance.html`. The heading is Atrium Finance. The board line is "Hotel books are not open on this desk." Opening https://beta.wolfcommand.net/ now 302s to that same page after she is signed in.

## Routing matrix

Checked against the live assignments. Direct `/`, `/index.html`, refresh of the own page, sign-out then signed-in `/`, deep link to the own page, and a forbidden page. Owner still opens `/wolf` and can still open Content.

| Person | Primary assignment | `/` 302 | Own page | Also opens | Denied pages (HTML) | Denied API (JSON) |
| --- | --- | --- | --- | --- | --- | --- |
| Zayen | `ASG-ZAYEN-FIN-1` Atrium Finance Officer, scope `SCOPE-AMG-FINANCE` | `/amg/finance` | `/amg/finance` | — | `/ggv/finance`, `/bzg/uma-blu`, `/wolf`, `/staff-ops-routing` | `/api/core/roles` |
| Haikal | `ASG-HAIKAL-CD-1` Creative Director | `/content-2.0` | `/content-2.0` | — | `/wolf`, `/ggv/finance`, `/amg/finance` | `/api/amg/finance` |
| Misa | `ASG-MISA-CD-1` Creative Director | `/content-2.0` | `/content-2.0` | — | `/wolf`, `/amg/finance`, `/ggv/finance` | `/api/core/roles` |
| Yudi | `ASG-YUDI-CREATOR-1` Content Creator | `/content-2.0` | `/content-2.0` | — | `/ggv/finance`, `/wolf` | `/api/amg/finance` |
| Devi | `ASG-DEVI-FB-OPS-1` BZG F&B operations lead | `/bzg/uma-blu` | `/bzg/uma-blu` | — | `/content-2.0`, `/ggv/finance`, `/wolf`, `/amg/finance` | `/api/amg/finance` |
| Amanda | `ASG-AMANDA-CM-1` Content Management, primary. `ASG-AMANDA-GGV-FIN-1` GGV Finance Operator is not primary | `/content-2.0` | `/content-2.0` | `/ggv/finance` | `/amg/finance`, `/wolf` | `/api/amg/finance` |
| Owner (`PERS-MATT`) | `ASG-MATT-OWNER-1` Owner / Executive | `/wolf` | `/wolf` | `/content-2.0` | — | — |

Unsigned `/` stays 403. `GET /api/health` stays 200.

# P3 — Staff home and My Work — 27 Sep 2026

Decision served: 2026-09-24 People Are Not Roles, extending the 2026-09-22 Empire Home. One daily page over Wolf Core. Not a new task database.

ENGINEERING PASS. Not staff ready. Not human commissioned.

Production `:8787` stayed on pid 15975. Beta `:8788` was restarted by launchd after the old listener (pid 47662) was stopped. It came back as pid 1413, still `scripts/serve_beta.py`, still Cloudflare fail-closed. No money, bank, or payment action. No NAS write.

## BEFORE

Staff did not have one daily page.

- `/staff-ops-routing` is a routing desk. It names seats (`PERS-DEVI`, name tokens) and speaks in pack codes.
- Shell Home still sends known people to the older desks: Creative Director to `/content-2.0`, BZG F&B Operations Lead to `/bzg/uma-blu`, GGV and Atrium seats to their pack desks, Owner to `/wolf`.
- `/wolf` is the Owner Empire page. It opens on engineering boards (progress percent, radar, pack handoffs), not a plain pulse.
- Wolf Core on the Beta catalog, counted at the start of this run: `core_work_items` 0, `core_approval_requests` 0, `core_governance_exceptions` 0, `core_evidence_records` 1 (a lead demo row). There is no notification table.
- Live seats: Haikal on Creative Director (`ROLE-GGV-CREATIVE-DIRECTOR`, `ASG-HAIKAL-CD-1`). Devi on BZG F&B Operations Lead (`ASG-DEVI-FB-OPS-1`) with scopes `SCOPE-BZG-FB` and `SCOPE-BZG-UMA`. Both of those scopes target the Uma Blu brand only. Matt on Owner / Executive. The external accountant role `ROLE-GGV-EXTERNAL-ACCOUNTANT` exists with position `POS-GGV-EXT-ACCT` and scope `SCOPE-GGV-FINANCE`. Nobody is assigned to it.

## BUILT-REPAIRED

- `/my-work` and `GET /api/staff/home`. Reads `org_persons`, `org_roles`, `org_assignments`, `org_scopes`, `core_work_items`, `core_approval_requests`, `core_governance_exceptions`, and `core_evidence_records`. Writes are refused (405). No second task table.
- Role picks the page. The person's name is only the greeting.
  - Creative Director: four questions, link "Open the content library". No finance, bank, or governance authority.
  - BZG F&B Operations Lead: same four questions across the scopes on the assignment. Today that is Uma Blu, with the link "Open today's Uma Blu work". The page does not call the seat an Uma-only viewer. It does not grant finance, bank, or governance authority.
  - Finance (external accountant role): four questions, link "Open finance notes". Read and review only. Cannot pay, change a bank account, or change a governance rule. The existing finance gate now allows `/my-work` and `/api/staff/home` so that role can open this page. It still blocks the rest of Wolf.
  - Owner: `/wolf` leads with pulse — what's happening, what's wrong, what needs your decision, what's blocked, what improved, money or control at risk. Not the staff questions. The older empire boards remain underneath.
- Empty lists say so. Demo and fixture rows are left out. Counts are not invented. `staff_ready` and `human_commissioned` stay false.
- A person who is not in the old name map gets their shell audience from the role on their assignment. Known seats keep the audiences they already had.
- The catalog allows only one active primary assignment per position. The replacement proof therefore used a second position with the same Creative Director role and the same scopes, then removed the person, assignment, and position.

## VERIFIED

```
python3 scripts/tests/test_staff_home.py | tail -3
PASS  prod 8787 up
PASS  beta 8788 up
PASS=89 FAIL=0
EXIT: SUCCESS
```

The test covers the live catalog seats, a replacement Creative Director whose experience fingerprint matches Haikal's with the name removed, a scratch work item that only the person who owns it can see, a temporary finance seat, then removal of both temporary people. Headless Chrome (390px and 1280px) on the Beta handler checked the four roles. Sideways scroll marker stayed `no`.

Live Beta after the restart, unsigned:

```
curl -sS -D - http://127.0.0.1:8788/api/staff/home
HTTP/1.0 403 Forbidden
{"ok": false, "error": "forbidden", "message": "Sign in required.", "staff_ready": false, "human_commissioned": false}

curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8788/my-work
403
```

Listeners after the restart:

```
Python 15975 127.0.0.1:8787
Python 1413  127.0.0.1:8788
```

Role HTML was not signed in through Cloudflare on `:8788`. That listener has no `BETA_AUTH_MODE=development_assertion`. The role proof used the same Beta handler on an ephemeral port with a development subject header. Temporary rows were removed. Leftover `PERS-P3-*`, `POS-P3-CD-1`, and `WI-P3-SCRATCH`: none.

## STAFF READY?

NO.

The page loads and the role split is proven, but a person opening it tonight sees an empty day. Wolf Core has no open work, no pending approvals, and no governance exceptions. The older desks (content library, Uma Blu today, finance notes) are linked, and they still hold the daily work. Shell Home was not switched, so known staff are not dropped on `/my-work` when they sign in. Cloudflare sign-in of the four roles on `:8788` was not done.

## HUMAN COMMISSIONED?

NO

## BLOCKERS

- BLOCKER: no real work items, approvals, or exceptions in Wolf Core. The four questions and the owner pulse stay empty until those records exist. This pack does not invent them.
- BLOCKER: there is no notification store. The page says "No notifications." A new notification database was not created.
- BLOCKER: `SCOPE-BZG-FB` is labelled for BZG F&B venues and its only brand target is Uma Blu. Other venues are not on this assignment. Scope targets were not widened.
- BLOCKER: `SCOPE-GGV-FINANCE` is labelled "GGV Finance only" and its target is the whole GGV entity. The target was not changed.
- BLOCKER: nobody is seated on the external accountant role. The finance proof was a temporary person, then removed.
- BLOCKER: `:8788` role screens need a Cloudflare sign-in. Development subject headers are ignored there.
- Remaining name coupling sits on the older routing desk (`staff_ops_routing` still matches `PERS-DEVI` and first-name tokens). The new page does not.

## NEXT HUMAN TEST

1. Sign in on Beta `:8788` as the Creative Director and open `/my-work`. Expect "Hello, Haikal", role Creative Director, the four questions saying nothing is assigned, and one link into the content library.
2. Sign in as the BZG F&B Operations Lead and open `/my-work`. Expect Uma Blu as the venue, "Open today's Uma Blu work", and no finance, bank, or owner pulse.
3. Seat a real person on `POS-GGV-EXT-ACCT` with `SCOPE-GGV-FINANCE` before expecting a finance login. Until then there is no finance person to sign in.
4. Sign in as Owner and open `/wolf`. Expect the six pulse lines first, each saying nothing is on record. Do not treat the older percent and radar boards under them as the pulse.

## FOUNDER DEPENDENCY

- Daily list for a seated role: ELIMINATE. The page follows the role and the assignment. It does not need Matt to route the day.
- Payment, bank changes, and governance authority: RETAIN. Those stay off staff roles. The owner role still holds governance authorise. Nothing here gives Matt a new daily step to make the page green.
- Finance note review: AUGMENT. The accountant role can read and review notes. Paying stays retained.
- Empty Wolf Core records: RETAIN. Someone has to enter real work. The page will not fill the gap.
- Owner pulse: RETAIN. What needs the owner's decision stays on the owner role.

RESULT: PASS

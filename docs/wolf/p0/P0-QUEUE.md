# P0 execution queue

SYSTEM = 19.65 / 77 = 25.52% ; STAFF READY = 0 ; HUMAN COMMISSIONED = 0 ; OPERATING ADOPTION = NOT MEASURED

Pack S2. Owner brief 27 Sep 2026 16:32 WITA. This is the one execution queue. Rule W3-P5-PRIORITY-v1. The ledger score was not raised.

Register count is **12**. `build_war_room()` in S1 returned P0 12, P1 20, P2 42, P3 3. The closed set is CAP-CORE-01 through CAP-CORE-10, plus CAP-MSC-02 and CAP-INTG-07. There is no thirteenth P0.

CAP-CORE-02 is READY_FOR_HUMAN. CAP-INTG-07 is BLOCKED_OWNER. CAP-MSC-02 stays OPEN after the deny prove in commit `025dd13`. The other nine stay OPEN. Staff ready, human commissioned, and operating adoption stay unset. None of these twelve is waiting on a named external provider.

Order is the critical path. A prerequisite is another P0 the next bar actually waits on. The catalog records no extra prerequisite inside the kernel, because those rows are already PROVEN or READY. That does not make the deployed observation done.

## 1. CAP-CORE-02 — Person & Auth Identity

- Current state: SYSTEM READY (1.00). Staff ready no. Human commissioned no. `test_real_auth_binding.py` PASS=51. Unsigned `GET /signout` on Beta `:8788` pid 59914 is 302 to the Access application logout. Unsigned and a bad JWT stay 403 on `/api/core/me`. No seated 200 was observed. There is no `ROLE-OWNER` row. Authorization is `person_id` plus assignment, not a name.
- Exact missing evidence: a real Cloudflare session for Haikal, Devi, and Matt, the landing and cross-role statuses, and the same route denied after Sign out.
- Cursor work: done in commit `8247252`. Evidence: `docs/wolf/p0/P0-CAP-CORE-02-RESULT.md`. Human test: `docs/wolf/p0/HUMAN-TESTS.md`. Do not mark anyone commissioned.
- Human work: one minute, after sign-out exists, on `https://beta.wolfcommand.net`. Haikal signs in and expects `/content-2.0`, denied on `/bzg/uma-blu`, `/wolf`, and `/ggv/finance`. Devi signs in and expects `/bzg/uma-blu`, denied on `/content-2.0`, `/wolf`, and `/ggv/finance`. Matt signs in and expects `/wolf`. Each person signs out. Record the statuses. The walk does not raise SYSTEM.
- External dependency: none.
- Prerequisite: none.
- Closure test: unsigned and a bad JWT stay 403 on `/api/core/me`. After each real session, landing and cross-role denial match the walk. After sign-out, the same route is denied. The local verifier is not this test.
- Target: READY_FOR_HUMAN. Status: READY_FOR_HUMAN. Commit: `8247252`.

## 2. CAP-INTG-07 — Secrets & Environment Separation

- Current state: SYSTEM SPECIFIED (0.05). The 27 Sep search named `~/.openclaw/credentials/` (decision 2026-07-21, plaintext, 30 JSON files). 1Password has no account. The keychain service `wolf-secrets-vault` encrypts off-site copies. It is not a vault product. Footage crypt, rclone, and the Atrium scratch backup are not this capability. No second vault was built.
- Exact missing evidence: a vault product Matt names, then a rotation and Dev/Beta/Prod separation prove. The repo-check test is not that prove.
- Cursor work: done. Evidence: `docs/wolf/p0/P0-CAP-INTG-07-RESULT.md`. The ledger was not edited.
- Human work: Matt names the vault product, or records that none is authorised.
- External dependency: none.
- Prerequisite: none.
- Closure test: the search names the store, with no secret value in the note. The ledger stays SPECIFIED. A passing repo-check test does not close this item.
- Target: BLOCKED_OWNER. Status: BLOCKED_OWNER. Commit: `44cd296`.

## 3. CAP-MSC-02 — Access & Cloudflare Posture

- Current state: SYSTEM BUILT (0.25). The deny prove is recorded. On Beta `:8788` pid 59914, unsigned, a spoofed email header, `X-Wolf-Subject`, and `Cf-Access-Jwt-Assertion: a.b.c` are 403 on `/api/core/me`, `/api/msc/posture`, and `/wolf`. The public hostname returns 302 to the Access login for those three paths. Access includes were not changed. No seated 200 was observed.
- Exact missing evidence: a review note that is not this queue, binding that deny prove to CAP-MSC-02. The 2026-09-20 review covers the empty framework and does not bind this prove. Seated allow and cross-role denial wait on the CAP-CORE-02 walk.
- Cursor work: done for the deny slice in commit `025dd13`. Evidence: `docs/wolf/p0/P0-CAP-MSC-02-RESULT.md`. Do not repeat the curl. Do not write the review. Do not call Grok. Do not raise the ledger.
- Human work: none for the deny prove. A seated observation uses the CAP-CORE-02 session and is not commissioning. The review is not that walk.
- External dependency: none.
- Prerequisite: CAP-CORE-02.
- Closure test: the deny cases exit 0, and a review note that is not this queue binds the result to CAP-MSC-02. The test half passed (`SUMMARY pass=38 fail=0`). The review half is absent, so the row stays OPEN. This queue does not raise the ledger.
- Target: CLOSED. Status: OPEN. Commit: `025dd13`. Remaining: the review note.

## 4. CAP-CORE-01 — Organisation Registry

- Current state: SYSTEM PROVEN (0.80). `scripts/core/organisation.py` and `test_org_registry.py`. D1 kept PROVEN. `GET /api/core/entities/ENT-NOPE` is HTTP 404.
- Exact missing evidence: the live org UI on Beta under a verified person. Deployed-route proof is FAIL. A development-subject 200 is not that proof.
- Cursor work: after a real session, record the org route status on Beta. Do not send `X-Wolf-Subject`.
- Human work: the session is CAP-CORE-02. No separate org acceptance.
- External dependency: none.
- Prerequisite: CAP-CORE-02.
- Closure test: the Beta status under the real session is recorded, including a denial for a person without organisation read. Unsigned stays fail-closed.
- Target: CLOSED. Status: OPEN.

## 5. CAP-CORE-03 — Role / Position / Assignment

- Current state: SYSTEM PROVEN (0.80). `ASG-HAIKAL-VE-1` is ended. The active seat is `ASG-HAIKAL-CD-1`. People are not roles.
- Exact missing evidence: a runtime board prove on Beta under a verified person.
- Cursor work: record the board for an existing person. Do not create a person. Do not move a primary assignment.
- Human work: none for the observation. Changing a primary assignment is a separate owner decision.
- External dependency: none.
- Prerequisite: CAP-CORE-01, CAP-CORE-02.
- Closure test: Beta shows the stored active assignment and does not show the ended assignment as active. No new person row.
- Target: CLOSED. Status: OPEN.

## 6. CAP-CORE-04 — Permission & Authority Engine

- Current state: SYSTEM PROVEN (0.80). The full seat matrix was not re-run on Beta. `ROLE-GGV-CREATIVE-DIRECTOR` does not hold `organisation.entity.read`. The ended edit grant does not apply.
- Exact missing evidence: allow and deny on Beta for the existing seats, under a verified person. The D3 catalog projection is not that HTTP proof.
- Cursor work: record allow and deny for `PERS-HAIKAL`, `PERS-DEVI`, and `PERS-MATT` only. Do not add a grant. Do not authorize by display name.
- Human work: the three sign-ins are CAP-CORE-02. This item records the statuses. It does not commission the people.
- External dependency: none.
- Prerequisite: CAP-CORE-03.
- Closure test: recorded statuses match the grants already on those assignments. Unsigned stays 403.
- Target: CLOSED. Status: OPEN.

## 7. CAP-CORE-05 — Authority Limits Evaluator

- Current state: SYSTEM PROVEN (0.80). Live `org_authority_limits` count is 0. The ledger says that zero is configuration, not maturity.
- Exact missing evidence: a broader runtime prove on Beta. No limit row exists. A displayed 0 is not a chosen tolerance.
- Cursor work: prove a denial when no limit row exists, on a temporary catalog, and record that the live table is still empty. Do not insert a limit.
- Human work: none.
- External dependency: none.
- Prerequisite: CAP-CORE-04.
- Closure test: the action is denied, and the live count is still 0. The empty table does not have to be filled before this item can close.
- Target: CLOSED. Status: OPEN.

## 8. CAP-CORE-06 — Work Items / Promises / Decisions

- Current state: SYSTEM PROVEN (0.80). The work-item primitive and its tests exist. Staff-usable is not the definition of PROVEN.
- Exact missing evidence: an operator trail across domains on the Beta runtime.
- Cursor work: trace one existing work item on a temporary catalog, then read that same shape on Beta under a real session. Do not create a live work item for the prove.
- Human work: none beyond the CAP-CORE-02 session used for the Beta read.
- External dependency: none.
- Prerequisite: CAP-CORE-02.
- Closure test: the temporary trail has the stored states, the live work-item count is unchanged, and the Beta read matches the stored row.
- Target: CLOSED. Status: OPEN.

## 9. CAP-CORE-07 — Approval Engine

- Current state: SYSTEM PROVEN (0.80). Live `core_approval_requests` is 0. Live `core_approval_decisions` is 6. Wide production policy packs are the READY bar.
- Exact missing evidence: those packs, and a deployed observation. Inventing a pack would be a fake policy.
- Cursor work: record the approval route on Beta after the real session. Do not insert a policy row.
- Human work: Matt approves a production policy pack, or records that none is authorised.
- External dependency: none.
- Prerequisite: CAP-CORE-06.
- Closure test: Beta shows the engine, live `core_approval_requests` is still 0, and a pack exists only if Matt authored it.
- Target: BLOCKED_OWNER. Status: OPEN.

## 10. CAP-CORE-08 — Segregation of Duties

- Current state: SYSTEM PROVEN (0.80). Broader finance SoD live packs are the READY bar.
- Exact missing evidence: those finance packs on the live path, plus deployed proof. None was added.
- Cursor work: show the existing deny (a submitter cannot verify their own close) on a temporary catalog. Do not add a finance pack. Do not move money.
- Human work: a broader finance pack, if one is required, is Matt's policy.
- External dependency: none.
- Prerequisite: CAP-CORE-04, CAP-CORE-07.
- Closure test: the temporary self-close deny still fails closed, and no new SoD pack was written to the live catalog.
- Target: BLOCKED_OWNER. Status: OPEN.

## 11. CAP-CORE-09 — Evidence Requirements

- Current state: SYSTEM PROVEN (0.80). Live `core_evidence_records` is 3. Universal evidence packs on all material actions are the READY bar.
- Exact missing evidence: which material actions already require evidence, and which do not. The three stored records are not that list.
- Cursor work: write that list from the code and the tests. Do not invent evidence rows.
- Human work: none until the list exists.
- External dependency: none.
- Prerequisite: CAP-CORE-07.
- Closure test: every material action is named as gated or not gated, and the live evidence count is still 3.
- Target: CLOSED. Status: OPEN.

## 12. CAP-CORE-10 — Exception / Override Governance

- Current state: SYSTEM PROVEN (0.80). Live `core_governance_exceptions` is 2. An operating review cadence is the READY bar.
- Exact missing evidence: that cadence, and a deployed view of the two existing exceptions. The two rows are not a cadence.
- Cursor work: show the existing exception read on Beta after the real session. Do not add a row.
- Human work: a person reviews the real exceptions on a repeating basis. That has not happened. It is not commissioning.
- External dependency: none.
- Prerequisite: CAP-CORE-09.
- Closure test: Beta shows the stored exceptions, the live count is still 2, and the cadence is not marked done without a person having run it.
- Target: READY_FOR_HUMAN. Status: OPEN.

## Cheap independent P1

These five do not edit the kernel. They are not a reason to skip an open P0.

1. CAP-GGV-02 Publish Gate. SYSTEM READY. The round-3 content walk is human. Do not hold it for The One = 0, 4,787 unknown brand, or 124 preview failures.
2. CAP-BZG-03 Venue Daily Close. SYSTEM READY. The absent policy now says BLOCKED BY BUSINESS POLICY. Do not invent a threshold, seat a closer, write ESB, or run a live close.
3. CAP-INTG-01 Yanolja. SYSTEM ABSENT. Leave it. Do not invent a feed.
4. CAP-FIN-03 accountant seat. `POS-GGV-EXT-ACCT` is empty. Do not invent a person. Amanda's content grant is not that seat.
5. CAP-FIN-01 books. Leave UNAVAILABLE. Do not type a balance.

CAP-STRAT-02 is not on this list. It requires CAP-CORE-01, CAP-CORE-06, and CAP-CORE-07.

## Variance sentence

When `venue_close_variance_policies` has no rows, the operator sentence is **BLOCKED BY BUSINESS POLICY**. `live_variance_threshold` remains the row count. That count is 0. It is not a tolerance.

Checked this session:

- `test_uma_blu_daily_close.py`: 71 passed, 0 failed, including the display assertion. Live policy count stayed 0.
- `test_uma_daily_loop_finish.py`: PASS=47 FAIL=0, including `lead-close shows BLOCKED BY BUSINESS POLICY`. Production pid 15975 and Beta pid 35844 were unchanged during that run.
- `test_progress_dashboard.py`: 198 passed, 0 failed, including the Empire variance sentence.
- `test_uma_ops_console.py`: PASS=24 FAIL=0.
- `test_blocker_explain.py`: PASS=55 FAIL=1. The failure is `issues page keeps Example label` in `dashboards/bzg-uma-blu-issues.html`, which this pack did not edit. The new close-policy assertions passed. Not repaired.

Beta `:8788` was restarted with `launchctl kickstart -k gui/501/net.wolfcommand.serve-beta` so the honesty route loaded the new field. Production `:8787` stayed pid 15975 (`serve.py`). Beta came back as pid 58953 (`scripts/serve_beta.py`).

Unsigned on pid 58953:

- `GET /api/venue-close/honesty` 200, `variance_policy_display` = `BLOCKED BY BUSINESS POLICY`, `live_variance_threshold` = 0
- `GET /uma-blu-close` 403
- `GET /uma-blu-close.html` 200, the phrase is in the body, the old "No variance policy set" sentence is not
- `GET /signout` 404

RESULT: PASS

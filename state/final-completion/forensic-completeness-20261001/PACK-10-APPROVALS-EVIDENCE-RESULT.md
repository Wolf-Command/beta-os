# Pack 10 — Approvals and evidence

Eng proof only. `staff_ready` stays false. Not HUMAN_PROVEN. A named person still has to click. Prod `:8787` was health-checked and not restarted. No authority limit was written.

## Authority

Source: `catalog/content_library.sqlite`, opened read-only. The catalog mtime did not change.

`org_authority_limits` count is 0. Active threshold is null. State FAIL_CLOSED.

`within_authority` for `PERS-MATT` / `work.complete` / `ENT-BZG`, probed with petty movement `PETTY-UMA-2321496C6D` amount 50000 and currency null, returns `higher_approval_required` / `no_matching_authority_limit`. `matched_limit` is null. That amount was not stored as a limit.

`core_delegations` count is 0.

## Who can decide

`approval.decide`, read from RBAC on the same connection:

| Person | ENT-BZG | ENT-AMG | ENT-GGV |
|---|---|---|---|
| PERS-MATT | allow | allow | allow |
| PERS-DEVI | role_lacks_permission | denied | denied |
| PERS-ZAYEN | denied | role_lacks_permission | denied |
| PERS-AMANDA | denied | permission_without_matching_scope | allow |
| PERS-ZENITALFATHAN | denied | denied | denied |

Matt holding `approval.decide` does not grant an amount. The amount gate above still denies.

Pack 5 finance seats, re-read: Zayen `ENT-GGV` false. Amanda `ENT-AMG` false. Books journal `JRN-ATRIUMSOD1B-COMM1` stays segregated, preparer `PERS-ZENITALFATHAN`. Self journal `JRN-ATRIUMSOD1B-SELF` has no approver. Books mtime did not change. Xero stays off.

A temp review file, not the catalog, returned `entity_denied` for Zayen on `ENT-GGV` and `self_approval_denied` when the producer approved their own pending row. That row stayed PENDING.

## The one live request

`core_approval_requests` count is 1.

`APR-292cc664-f235-4bef-93eb-78a6abbf43bd`, GENERAL, `ENT-BZG`, requester `PERS-DEVI`, decider `PERS-MATT`, status APPROVED, material amount null. `self_approved` is false. No second request was created.

`core_approval_decisions` has 10 rows. 9 of them point at request ids that are not in `core_approval_requests`, decided by `PERS-P4-APPROVER-2` and `PERS-P4-DELEGATE`. Those person ids are not in `org_persons`. They are leftover fixtures. They are not who-can-approve.

## Evidence

Receipt `EVD-372162c1-d0ac-42a6-b5f3-5959c11f4621` is an ACTIVE `receiving_document` on `RCP-d8d0d12a-903f-4f50-aa5e-216ed31394fe`. Petty photo `EVD-9498bb75-294c-4924-b30b-8cef0cab5351` is attached to Alchemist petty cash id 451.

Both Uma closes still have `declared_cash_evidence_id` null. State FAIL_CLOSED. No till figure was attached.

The one ACTIVE requirement is `EVR-HABITAT-CONTENT-PUBLISH` (`ENT-GGV`, `content_draft`, min 1). Evaluating it for a card that does not exist returns `missing_required_evidence`. Publish was not executed.

## HTTP

Verified 2026-10-01 on `:8788` after `launchctl kickstart` of `net.wolfcommand.serve-beta`. No Cloudflare JWT was presented. Auth mode was not changed.

| Path | Result |
|---|---|
| `GET /api/approvals/evidence` | 200, limits 0, requests 1, declared cash unattached, staff_ready false |
| `GET /approvals/evidence` | 200, five tiles, none start open |
| `POST /api/approvals/evidence` | 405 `writes_off` |
| `GET /api/health` `:8788` and `:8787` | 200 |

The page script loads the JSON. A browser click-through was not done.

## Tests

`scripts/tests/test_approvals_evidence_pack10.py`: 27 passed, 0 failed.

## Left undone

An authority limit above zero. A delegation. A human click. Declared-cash evidence. A content publish. A new live approval. `staff_ready`.

## NEXT — forensic checkpoint

The original queue is complete through pack 10. No pack 11 is defined here. Peaches chooses the next rebuild slice from the missing-function register.

Eng-proved, `staff_ready` false, not human-clicked:

1. Owner cockpit — read cards, UNKNOWN lines kept.
2. Uma buy → receive → petty → close — one real chain. Declared cash still missing.
3. Atrium sales desk — vacant-versus-rooms. In-house UNKNOWN.
4. Content tick → draft — Habitat cycle. Publish stays off.
5. Atrium finance screens — SoD held. Xero and payroll off.
6. GGV nota — capture on a catalog copy. Issue blocked. Live notas stay 0.
7. Guest stay — Yanolja vacant-versus-rooms. Pre-arrival and post-stay UNAVAILABLE.
8. Recipe variance — theoretical sample only. Variance amount UNKNOWN.
9. Pre-open config — six PRE-OPENING rows, blank close, board title Blu Zone Restaurant. Sales null.
10. Approvals and evidence — limits 0, one live GENERAL request, evidence fail-closed where the file is missing.

Register after this pack, counted from `MISSING-FUNCTION-REGISTER.jsonl`: PARTIAL 61, SHELL 42, MISSING 32, FUNCTIONAL_REAL_DATA 23, READ_ONLY_MIRROR 19. 177 lines.

`need.*` rows still MISSING: maintenance, security, events, tours, month-end shareholder pack, content learn-back, CRM identity, housekeeping, menu engineering, sale readiness. HR stays out. Amount authority, declared cash, in-house guests, recipe variance, pre-open sales, and publish remain open inside the packs above.

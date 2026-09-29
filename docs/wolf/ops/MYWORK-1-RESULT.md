# MYWORK-1 result

29 Sep 2026. Beta only, branch `build/wolf-command-rebuild`. P0 UNIVERSAL MY WORK — extend Wolf Core Work Items / Assignment / Scope / RBAC / Evidence / Audit / Delegation / Approval. No second task engine. Production `:8787` pid **15975** unchanged. Atrium sidecar `:8790` pid **96416** unchanged. Nobody marked `staff_ready` or `human_commissioned`. No ClickUp / Alchemist / ESB / Gmail / Xero writes. No push.

Beta listener restarted detached from `scripts/serve_beta.py` with `BETA_AUTH_MODE` unset. Unsigned `GET /api/health` is 200. Unsigned `GET /wolf` is 403.

Decision served: Matt 29 Sep 2026 07:20 — P0 UNIVERSAL MY WORK (extends OPSFIX-3 / LEGACY-1 on `build/wolf-command-rebuild`).

## Active people who can receive work

| Name | Assignment(s) | Role |
| --- | --- | --- |
| Alam | ASG-ALAM-CREATOR-1 | Content Creator |
| Amanda | ASG-AMANDA-CM-1; ASG-AMANDA-GGV-FIN-1 | Content Management; GGV Finance Operator |
| Frail | ASG-FRAIL-CD-1 | Creative Director |
| Gery | ASG-GERY-CREATOR-1 | Content Creator |
| Haikal | ASG-HAIKAL-CD-1 | Creative Director |
| Matthew Goss | ASG-MATT-OWNER-1 (+ intel fixture) | Owner / Executive — OVERWATCH |
| Misa | ASG-MISA-CD-1 | Creative Director |
| Nata | ASG-NATA-CREATOR-1 | Content Creator |
| Ni Putu Devi Parwati | ASG-DEVI-FB-OPS-1; ASG-DEVI-CLOSER-UMA-1 | BZG F&B Ops Lead; Uma Blu Daily Closer |
| Rapp | ASG-RAPP-CREATOR-1 | Content Creator |
| TJ | ASG-TJ-CREATOR-1 | Content Creator |
| Yudi | ASG-YUDI-CREATOR-1 | Content Creator |
| Zarah | ASG-ZARAH-CD-1 | Creative Director |
| Zayen | ASG-ZAYEN-FC-1 | Atrium Financial Controller |

(Demo/fixture seats excluded.)

## Parts

1. **FIXED.** Zayen: prior `ASG-ZAYEN-FIN-1` (Finance Officer) ended with reason preserved; new `ASG-ZAYEN-FC-1` / `ROLE-AMG-FINANCIAL-CONTROLLER`. Authority = existing Atrium matrix (draft/read). Denied: pay, bank, approve/post, identity/admin, Owner.

2. **FIXED.** Devi: `ASG-DEVI-CLOSER-UMA-1` on `POS-BZG-CLOSER-UMA-1`. F&B Ops Lead kept. Closers are `venue_closer_roster` (add rows later, no code change). Cash-variance tolerance **UNSET**; Daily Close shows open policy control; no invented number.

3. **FIXED.** Matt OVERWATCH: `SCOPE-AMG-FINANCE` + `SCOPE-AMG-ATR-DAY` attached to Owner assignment (BZG/GGV already covered). Visibility / exception / intervene within policy. Routine work does not default-route to him.

4. **FIXED.** Canonical model stays `core_work_items` (+ `core_work_delegations`, evidence files). PERSON → ASSIGNMENT → ROLE → SCOPE → WORK ITEM → EVIDENCE → COMPLETION → VERIFICATION. Work survives staff replacement via assignment/role inheritance.

5. **FIXED.** Universal My Work sections: TODAY, DO THIS NEXT, NEEDS ATTENTION, WAITING, COMPLETED. Phone-first (390px shot).

6. **FIXED.** Cards show what / requested by / owner / due / company-site-dept / priority / instructions / evidence / status / what happens next.

7. **FIXED.** Open → start → attach evidence (blob under NAS when mounted, else `state/work-evidence/blobs`) → DONE. States include WAITING / RETURNED / REASSIGNED. DONE ≠ VERIFIED. Audit on transitions.

8. **FIXED.** Delegation chain: accountable vs executor; hops with who/to/accepted/timestamps. Example Matt → Haikal → Yudi covered in tests.

9. **FIXED.** Assign-to-whom from `work.assign` / scope / Owner overwatch — not hardcoded department walls.

10. **FIXED.** Execution & Delegation Report at `/execution-report` + `GET /api/my-work/execution-report`. Plain factual sentences. No AI judgement labels.

11. **FIXED.** War Room GIVE THIS TO A HUMAN NOW reads real `origin=commissioning` Work Items (OPSFIX-3 test cards no longer the queue). DONE → evidence; verify PASS → VERIFIED HUMAN PASS; FAIL → repair item. Flags stay false. SYSTEM % unchanged on DONE.

12. **FIXED.** Commissioning tasks issued (28): Devi (Uma Today, Recipes, Purchasing, ESB sales, Daily Close UNSET parts); Zayen (Command, Journal draft, Ledger, Trial, AR/AP, Inventory, Reports, controls denied); Amanda (064A–066A, 067A if due); Haikal (My Work, Plan, Library, Habitat); other content seats My Work each.

13. **FIXED.** Legacy import from `state/legacy/proposed-migration.json`: imported **148**, unknown-review **5**, failed **0**. Provenance on each row. OBSOLETE not reactivated.

14. **FIXED.** ClickUp cut-line recorded at `state/legacy/clickup-cut-line.json` — no Wolf ClickUp writes/deps; history readable; nothing deleted.

15. **FIXED.** Derived-view stamps (`core_derived_view_stamps`): canonical change → STALE until refresh; My Work / War Room / execution report / Owner exceptions share one work state.

## Tests this session

| File | Result |
| --- | --- |
| `scripts/tests/test_mywork1_20260929.py` | SUMMARY pass=107 fail=0, RESULT: PASS |
| `scripts/tests/test_opsfix3_20260929.py` | SUMMARY pass=88 fail=0, RESULT: PASS |
| `scripts/tests/test_opsfix2_20260928.py` | SUMMARY pass=45 fail=0, RESULT: PASS |
| `scripts/tests/test_opsfix1_20260928.py` | SUMMARY pass=42 fail=0, RESULT: PASS |
| `scripts/tests/test_staff_access_20260928.py` | SUMMARY pass=275 fail=0 |
| `scripts/tests/test_role_routing_20260928.py` | SUMMARY pass=84 fail=0 |
| `scripts/tests/test_atrium_full_mount_20260928.py` | SUMMARY pass=79 fail=0 |
| `scripts/tests/test_umareal_20260928.py` | SUMMARY pass=85 fail=0 |
| `scripts/tests/test_opsaudit_20260928.py` | SUMMARY pass=109 fail=0, RESULT: PASS |

## Shots

`docs/wolf/ops/shots/mywork1-*.png`: Devi phone, Zayen, Amanda, Haikal, task+evidence, delegation chain, execution report, War Room tasks, Owner Command exceptions.

## Pids

| Process | Pid |
| --- | --- |
| Production `:8787` | 15975 (unchanged) |
| Atrium sidecar `:8790` | 96416 (unchanged) |
| Beta `:8788` | 59347 (replaced prior listener) |

## Commits

Local only. No push.

- `61edfa6804cf731823922f9f9ae64bdbe763bd58` — Extend Wolf Core into universal My Work with real commissioning tasks.
- `d2e2de73127ee4c585814552a2713f7500884e09` — Record MYWORK-1 commit hash in the result.
- `9425a297752f4b821c267c6e200db58106671f51` — Fix MYWORK-1 result commit hashes.
- `adde5873c344091f4b9fa4e2d7b026b8fd82f322` — List full MYWORK-1 result commit SHAs.

RESULT: PASS

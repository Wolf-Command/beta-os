# Breach J1 quiet probe — CLEAN

- **When:** 2026-09-29 ~08:20–08:35 WITA
- **Class:** quiet-probe / CLEAN (not a security finding)
- **Severity:** n/a
- **Status:** CLEAN · complete
- **Repo:** `/Users/wolfterminal/beta-os` branch `build/wolf-command-rebuild`
- **Tip:** `950b026` (moved since 28 Sep baseline `ab1009b`; 42 commits; tip date 2026-09-29 08:28 WITA)

## Checks run (read-only)

1. **Open findings:** Mac `FINDINGS-LATEST` Open RED/open: 0. Prior notes 2026-09-24 + 2026-09-25 + 2026-09-28 CLEAN only. No RED/open security finding.
2. **Tip-stomp smell (recent soft-applies):** Tip moved `ab1009b` → `950b026`. Dirty WT: docs/shots/ops/vesper/breach notes + backups — **no** allow/rbac/whoami/payment/finance grant code paths dirty. `scripts/core/rbac.py` untouched since baseline. `scripts/core/wolf_shell.py` +134/−4 (additive Atrium Finance audience/landing/crumbs, CONTENT-CREATOR + GGV/AMG finance role audience maps, assignment-primary audience preference, whoami hello helper) — **0** privilege +lines matching `payment.` / `finance.nota` / ALLOW grants. No bak/old-tip stomps under `scripts/core` or `catalog/`. Smell: **none** (staff-seat + My Work + Atrium mount packs; no tip-stomp of removed gates).
3. **Habitat/Selo client roles/persons:** none in `org_roles` / `org_persons` matching client/habitat/selo. `ROLE-LEAD-DEMO-FIXTURE` lead.* only — finance/payment DENY.
4. **clients ∩ finance grants:** **0** rows.
5. **Devi `PERS-DEVI` / `ROLE-BZG-FB-OPS-LEAD`:** active primary `ASG-DEVI-FB-OPS-1` → `POS-BZG-FB-OPS-1`. Secondary active `ASG-DEVI-CLOSER-UMA-1` → `ROLE-BZG-CLOSER` (close submit/read + work.* only). Role ALLOW count **10** ops (`bzg.pr.operator`, `venue.close.read/submit/resolve_exception`, `venue.receive`, `evidence.record.submit`, `work.create/read/update/complete`). `bzg.pr.payment_approve` **DENY** (`role_lacks_permission`). `venue.close.verify` **DENY**. `finance.nota.*` / `payment.*` **DENY**. No finance/atlas/money codes on either active role.
6. **GGV Finance nota:** Operating ALLOW on `ROLE-MATT` + `ROLE-CONTENT-MGMT` + `ROLE-GGV-FINANCE-OPERATOR` for `finance.nota.read/create/edit` + `finance.evidence.export`. Person evaluate ALLOW only `PERS-MATT` + `PERS-AMANDA` (Amanda also holds secondary `ASG-AMANDA-GGV-FIN-1` → `ROLE-GGV-FINANCE-OPERATOR`). `ROLE-GGV-EXTERNAL-ACCOUNTANT` read/review/export + `vendor.read` + `finance.invoice.read`; position `POS-GGV-EXT-ACCT` exists, **no person assignment**. Haikal/Misa/Devi/Lead-demo/Zayen nota+payment **DENY**. Matt+Amanda `payment.execute`/`payment.approve` **DENY**; **0** role grants on those codes. `bzg.pr.payment_approve` still ungated to any role (deny-by-default).
7. **Fail-closed:** empty person/permission → `missing_person_or_permission` deny; unknown person → `no_active_assignment`; unknown perm → `unknown_permission`. Anon `shell_whoami_payload(None)` → nested `whoami.wolf_authorized=false`, `whoami.pages=[]`, audience CLIENT projection only. Evaluator: `core.rbac.evaluate`.

8. **Observation (not RED):** Devi role ALLOW count 10 vs 28 Sep note “7 ops” — added `work.read/update/complete` from My Work pack; still ops-only class; critical DENYs unchanged. Amanda now also seated on `ROLE-GGV-FINANCE-OPERATOR` (secondary) — same person already had nota via CONTENT-MGMT; no new person gained nota. Zayen primary `ROLE-AMG-FINANCIAL-CONTROLLER` (Atrium draft/read; prior OFFICER assignment ENDED) — no GGV nota, no `payment.execute/approve`. Tip pin advanced 42 commits — staff access / Atrium mount / My Work / opsfix, not a privilege tip-stomp.

## Never done this tick
Fixes · live soft-apply · widen allows · money/CF/posts · Cipher access compile.

## Escalation
- Open RED/open: **0** → no Vesper escalate.
- Silent to Matthew.
- No SendToAgent in automation — Peaches ran Breach intent inline (same as 23–28 Sep).

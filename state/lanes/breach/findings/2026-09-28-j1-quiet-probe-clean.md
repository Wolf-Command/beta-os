# Breach J1 quiet probe — CLEAN

- **When:** 2026-09-28 ~08:20–08:35 WITA
- **Class:** quiet-probe / CLEAN (not a security finding)
- **Severity:** n/a
- **Status:** CLEAN · complete
- **Repo:** `/Users/wolfterminal/beta-os` branch `build/wolf-command-rebuild`
- **Tip:** `ab1009b` (moved since 25 Sep baseline `f3ab8f7`; 70 commits; tip date 2026-09-28 08:23 WITA)

## Checks run (read-only)

1. **Open findings:** Mac `FINDINGS-LATEST` Open RED/open: 0. Prior notes 2026-09-24 + 2026-09-25 CLEAN only. No RED/open security finding.
2. **Tip-stomp smell (recent soft-applies):** Tip moved `f3ab8f7` → `ab1009b`. Dirty WT: `serve_beta.py` (+SOP learn/acknowledge/use routes only), `core_mgmt_cluster.py`, `sop_factory.py`, tests — **no** allow/rbac/whoami/payment/finance grant paths. `rbac.py` / `wolf_shell.py` / catalog DB not dirty. Privilege-ish +lines in `wolf_shell.py`/`rbac.py` since baseline: **0**. No bak/old-tip stomps. Smell: **none** (additive independence/ledger packs; no tip-stomp of removed gates).
3. **Habitat/Selo client roles/persons:** none in `org_roles` / `org_persons` matching client/habitat/selo. `PERS-LEAD-DEMO` / `ROLE-LEAD-DEMO-FIXTURE` lead.* only — finance/payment DENY.
4. **clients ∩ finance grants:** **0** rows.
5. **Devi `PERS-DEVI` / `ROLE-BZG-FB-OPS-LEAD`:** active `ASG-DEVI-FB-OPS-1` → `POS-BZG-FB-OPS-1`. Role ALLOW count **7** ops (`bzg.pr.operator`, `venue.close.read/submit/resolve_exception`, `venue.receive`, `evidence.record.submit`, `work.create`). `bzg.pr.payment_approve` **DENY** (`role_lacks_permission`). `venue.close.verify` **DENY**. `finance.nota.*` / `payment.*` **DENY**. No finance/atlas/money codes granted.
6. **GGV Finance nota:** Operating ALLOW only on `ROLE-MATT` + `ROLE-CONTENT-MGMT` (Amanda `ASG-AMANDA-CM-1` → `POS-CONTENT-MGMT-1`) for `finance.nota.read/create/edit` + `finance.evidence.export`. `ROLE-GGV-EXTERNAL-ACCOUNTANT` read/review/export + `vendor.read` only; position `POS-GGV-EXT-ACCT` exists, **no person assignment**. Haikal/Misa/Devi/Lead-demo nota+payment **DENY**. Matt+Amanda `payment.execute`/`payment.approve` **DENY**; **0** role grants on those codes.
7. **Fail-closed:** empty person/permission → `missing_person_or_permission` deny; unknown person → `no_active_assignment`; unknown perm → `unknown_permission`. Anon `shell_whoami_payload(None)` → `wolf_authorized=false`, `pages=[]`, audience CLIENT projection only. Evaluator: `core.rbac.evaluate`.

8. **Observation (not RED):** Devi role ALLOW count 7 vs 25 Sep note “12 ops perms” — still ops-only class; critical DENYs unchanged. `finance.nota.evidence.export` code is now `finance.evidence.export` (same allow set). Tip pin advanced 70 commits — commit hygiene / pack landings, not a privilege widen. `bzg.pr.payment_approve` still ungated to any role (deny-by-default).

## Never done this tick
Fixes · live soft-apply · widen allows · money/CF/posts · Cipher access compile.

## Escalation
- Open RED/open: **0** → no Vesper escalate.
- Silent to Matthew.
- No SendToAgent in automation — Peaches ran Breach intent inline (same as 23–25 Sep).

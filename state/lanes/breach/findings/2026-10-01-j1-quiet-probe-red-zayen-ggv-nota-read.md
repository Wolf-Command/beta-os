# Breach J1 quiet probe — RED

- **When:** 2026-10-01 ~08:25–08:28 WITA
- **Class:** quiet-probe / RED (security finding)
- **Severity:** RED
- **Status:** open (prior finding still reproduces; no new finding IDs)
- **Repo:** `/Users/wolfterminal/beta-os` branch `build/wolf-command-rebuild`
- **Tip:** `b3739a7` (moved since 30 Sep baseline `d8f6ecd`; 15 commits; tip date 2026-09-30 11:02 WITA)

## Checks run (read-only)

1. **Open findings:** Box+Mac `FINDINGS-LATEST` at start Open RED/open: 1 — `BREACH-2026-09-30-J1-ZAYEN-GGV-NOTA-READ`. Prior notes include 2026-09-30 RED + earlier CLEAN. This probe **re-confirms** that RED still open (still reproduces); no NEW finding IDs opened.
2. **Tip-stomp smell (recent soft-applies):** Tip moved `d8f6ecd` → `b3739a7` (15 commits; verify packs + EXTERNAL-ROUTE-HEALTH + global app shell business switcher PARTIAL). Dirty WT at probe time: many dashboards/docs/shots + numerous `scripts/core/*` pack modules — **`scripts/core/rbac.py` clean vs HEAD and untouched since `d8f6ecd`**. `wolf_shell.py` since baseline: +614/−15 (shell/business switcher/audience surfaces) — **0** privilege +lines matching `payment.` / `finance.nota` / ALLOW grants. No bak/old-tip stomps under `scripts/core` or `catalog/`. Smell: **none** (not a tip-stomp of removed gates).
3. **Habitat/Selo client roles/persons:** none in `org_roles` / `org_persons` matching client/habitat/selo. `ROLE-LEAD-DEMO-FIXTURE` lead.* only (4 ALLOW) — finance/payment DENY for `PERS-LEAD-DEMO`.
4. **clients ∩ finance grants:** **0** rows.
5. **Devi `PERS-DEVI` / `ROLE-BZG-FB-OPS-LEAD`:** active primary `ASG-DEVI-FB-OPS-1` → `POS-BZG-FB-OPS-1`. Secondary active `ASG-DEVI-CLOSER-UMA-1` → `ROLE-BZG-CLOSER`. Role ALLOW count **10** ops (`bzg.pr.operator`, `venue.close.read/submit/resolve_exception`, `venue.receive`, `evidence.record.submit`, `work.create/read/update/complete`). `bzg.pr.payment_approve` **DENY** (`role_lacks_permission`). `venue.close.verify` **DENY**. `finance.nota.*` / `payment.*` **DENY**.
6. **GGV Finance nota:** create/edit ALLOW roles still `ROLE-MATT` + `ROLE-CONTENT-MGMT` + `ROLE-GGV-FINANCE-OPERATOR`. Person create/edit ALLOW only `PERS-MATT` + `PERS-AMANDA`. Haikal/Misa/Devi/Lead-demo nota+payment **DENY**. Matt+Amanda `payment.execute`/`payment.approve` **DENY**; **0** role grants on those codes. `bzg.pr.payment_approve` still ungated to any role (deny-by-default). `ROLE-GGV-EXTERNAL-ACCOUNTANT` + `ROLE-AMG-EXTERNAL-ACCOUNTANT` / `ROLE-BZG-EXTERNAL-ACCOUNTANT` hold read/review/export (+ vendor/invoice read); **0** person assignments. **`PERS-ZAYEN` still ALLOW** `finance.nota.read` / `finance.invoice.read` / `finance.evidence.export` via `ASG-ZAYEN-BZG-FC-1` → `ROLE-BZG-FINANCIAL-CONTROLLER` (`matched_scope_id=SCOPE-BZG-FINANCE`); create/edit/payment DENY.
7. **Fail-closed:** empty person/permission → `missing_person_or_permission` deny; unknown person → `no_active_assignment`; unknown perm → `unknown_permission`. Anon `shell_whoami_payload(None)` → nested `whoami.wolf_authorized=false`, `whoami.pages=[]`, audience CLIENT. Evaluator: `core.rbac.evaluate`.

## RED finding (still open — reproduces)

**ID:** BREACH-2026-09-30-J1-ZAYEN-GGV-NOTA-READ  
**Title:** Zayen gains GGV Finance nota/invoice read via secondary BZG FC seat (violates ZERO GGV Finance access)  
**Actor:** `PERS-ZAYEN`  
**Path (2026-10-01 re-verify):** `ASG-ZAYEN-BZG-FC-1` (ACTIVE secondary, created `2026-09-29T21:09:39+08:00`) → `ROLE-BZG-FINANCIAL-CONTROLLER` → ALLOW `finance.nota.read`, `finance.evidence.export`, `finance.invoice.read`, `vendor.read` (evaluate `permission=true`, `matched_scope_id=SCOPE-BZG-FINANCE`). AMG FC + temp AR paths alone still lack nota.  
**Impact:** Unchanged vs 30 Sep — person-level ALLOW is real GGV Finance read access against shared `finance.nota.*` codes. `finance.nota.create/edit` DENY; `payment.execute`/`payment.approve` DENY (0 role grants).  
**Baseline break:** Owner constitutional rule — Zayen ZERO GGV Finance access. 29 Sep CLEAN tip `950b026` had Zayen with no GGV nota; broke after BZG FC seed.  
**Evidence:** read-only `core.rbac.evaluate('PERS-ZAYEN', 'finance.nota.read')` → `allowed=true`; catalog `catalog/content_library.sqlite` org_* rows as above. Tip-stomp smell none.  
**Remediation:** out of Breach scope (no fixes this tick). Escalate Vesper → Peaches for Owner gate before any grant/assignment change.

## Observations (not RED / not new)

- Tip pin advanced 15 commits since 30 Sep RED baseline — shell/route/verify packs; not a privilege tip-stomp.
- Devi ALLOW set unchanged vs 29–30 Sep (10 ops + closer secondary).
- External accountant roles still unassigned (latent GGV nota codes on AMG/BZG external roles unchanged).
- No NEW Breach finding IDs this tick.

## Never done this tick
Fixes · live soft-apply · widen allows · money/CF/posts · Cipher access compile.

## Escalation
- Open RED/open: **1** → escalate to Vesper then Peaches (Breach does not message agents; no SendToAgent).
- Silent to Matthew (Peaches/Vesper path owns Owner brief).
- No SendToAgent in automation — Peaches ran Breach intent inline (same as 23–30 Sep).

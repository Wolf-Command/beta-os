# Breach J1 quiet probe — RED

- **When:** 2026-09-30 ~08:25–08:28 WITA
- **Class:** quiet-probe / RED (security finding)
- **Severity:** RED
- **Status:** open
- **Repo:** `/Users/wolfterminal/beta-os` branch `build/wolf-command-rebuild`
- **Tip:** `d8f6ecd` (moved since 29 Sep baseline `950b026`; 90 commits; tip date 2026-09-30 08:26 WITA)

## Checks run (read-only)

1. **Open findings:** Mac `FINDINGS-LATEST` at start Open RED/open: 0. Prior notes 2026-09-24 + 2026-09-25 + 2026-09-28 + 2026-09-29 CLEAN only. This probe opens **1** RED.
2. **Tip-stomp smell (recent soft-applies):** Tip moved `950b026` → `d8f6ecd` (90 commits; honesty/ops/pack landings). Dirty WT at probe time: docs/shots + final-completion pack state + untracked SOP/shots — **no** allow/rbac/whoami/payment/finance grant code paths dirty (`scripts/core/rbac.py` and `wolf_shell.py` clean vs HEAD). `scripts/core/rbac.py` untouched since baseline. `wolf_shell.py` since baseline: no privilege +lines matching `payment.` / `finance.nota` / ALLOW grants (path-norm only). No bak/old-tip stomps under `scripts/core` or `catalog/`. Smell: **none** (not a tip-stomp of removed gates).
3. **Habitat/Selo client roles/persons:** none in `org_roles` / `org_persons` matching client/habitat/selo. `ROLE-LEAD-DEMO-FIXTURE` lead.* only — finance/payment DENY.
4. **clients ∩ finance grants:** **0** rows.
5. **Devi `PERS-DEVI` / `ROLE-BZG-FB-OPS-LEAD`:** active primary `ASG-DEVI-FB-OPS-1` → `POS-BZG-FB-OPS-1`. Secondary active `ASG-DEVI-CLOSER-UMA-1` → `ROLE-BZG-CLOSER`. Role ALLOW count **10** ops (`bzg.pr.operator`, `venue.close.read/submit/resolve_exception`, `venue.receive`, `evidence.record.submit`, `work.create/read/update/complete`). `bzg.pr.payment_approve` **DENY** (`role_lacks_permission`). `venue.close.verify` **DENY**. `finance.nota.*` / `payment.*` **DENY**. No finance/atlas/money codes on either active role.
6. **GGV Finance nota (operating expect Matt+Amanda):** create/edit ALLOW roles still `ROLE-MATT` + `ROLE-CONTENT-MGMT` + `ROLE-GGV-FINANCE-OPERATOR`. Person create/edit ALLOW only `PERS-MATT` + `PERS-AMANDA`. Haikal/Misa/Devi/Lead-demo nota+payment **DENY**. Matt+Amanda `payment.execute`/`payment.approve` **DENY**; **0** role grants on those codes. `bzg.pr.payment_approve` still ungated to any role (deny-by-default). `ROLE-GGV-EXTERNAL-ACCOUNTANT` + new unassigned `ROLE-AMG-EXTERNAL-ACCOUNTANT` / `ROLE-BZG-EXTERNAL-ACCOUNTANT` hold read/review/export (+ vendor/invoice read); positions exist, **no person assignment**.
7. **Fail-closed:** empty person/permission → `missing_person_or_permission` deny; unknown person → `no_active_assignment`; unknown perm → `unknown_permission`. Anon `shell_whoami_payload(None)` → nested `whoami.wolf_authorized=false`, `whoami.pages=[]`, audience CLIENT. Evaluator: `core.rbac.evaluate`.

## RED finding (open)

**ID:** BREACH-2026-09-30-J1-ZAYEN-GGV-NOTA-READ  
**Title:** Zayen gains GGV Finance nota/invoice read via secondary BZG FC seat (violates ZERO GGV Finance access)  
**Actor:** `PERS-ZAYEN`  
**Path:** `ASG-ZAYEN-BZG-FC-1` (ACTIVE secondary, created `2026-09-29T21:09:39+08:00`, after 29 Sep J1 CLEAN) → `ROLE-BZG-FINANCIAL-CONTROLLER` → ALLOW `finance.nota.read`, `finance.evidence.export`, `finance.invoice.read`, `vendor.read` (evaluate path `permission=true`, `matched_scope_id=SCOPE-BZG-FINANCE`).  
**Impact:** `scripts/core/ggv_finance_nota.py` gates live GGV nota surfaces with `require(..., "finance.nota.read")` / related codes against `ENTITY_GGV` data — person-level ALLOW is real GGV Finance read access, not a BZG-only alias. `finance.nota.create/edit` still DENY; `payment.execute`/`payment.approve` still DENY (0 role grants).  
**Baseline break:** J1 check #7 + Owner constitutional rule — Zayen / Atrium (+ BZG FC) must have **ZERO GGV Finance access**. 29 Sep CLEAN explicitly recorded Zayen with no GGV nota.  
**Also seeded same stamp (`2026-09-29T21:09:39+08:00`):** `ROLE-BZG-FINANCIAL-CONTROLLER` grant bundle includes GGV-shared `finance.nota.read` / `finance.evidence.export` / `finance.invoice.read`; AMG/BZG EXTERNAL-ACCOUNTANT roles cloned with GGV nota read/review (unassigned — latent). BZG FC role also carries `atrium.journal.*` (cross-product observation under same seed).  
**Evidence:** read-only `core.rbac.evaluate('PERS-ZAYEN', 'finance.nota.read')` → `allowed=true`; catalog `catalog/content_library.sqlite` org_* rows as above. Tip-stomp smell none — this is grant/assignment seed after prior CLEAN, not a soft-apply of removed gates.  
**Remediation:** out of Breach scope (no fixes this tick). Escalate Vesper → Peaches for Owner gate before any grant/assignment change.

## Observations (not RED)

- Tip pin advanced 90 commits (FINAL COMPLETION / honesty packs) — not itself a privilege tip-stomp.
- Devi ALLOW set unchanged vs 29 Sep (10 ops + closer secondary).
- Atrium primary `ROLE-AMG-FINANCIAL-CONTROLLER` + temp AR alone still have empty GGV/nota/payment subset; bleed is via BZG FC secondary only.
- AMG/BZG EXTERNAL-ACCOUNTANT unassigned OK for person impact; still note GGV nota codes on non-GGV external roles as latent mis-seed.

## Never done this tick
Fixes · live soft-apply · widen allows · money/CF/posts · Cipher access compile.

## Escalation
- Open RED/open: **1** → escalate to Vesper then Peaches (Breach does not message agents; no SendToAgent).
- Silent to Matthew (Peaches/Vesper path owns Owner brief).
- No SendToAgent in automation — Peaches ran Breach intent inline (same as 23–29 Sep).

---

## OWNER ACCEPT — CLOSED REPAIRED+VERIFIED

Owner ACCEPT 2026-10-01T11:21:00+08:00 · Peaches 2026-10-01T11:23:30+08:00 · REPAIRED + VERIFIED (50/50 server-side) · KEEP ASG-ZAYEN-BZG-FC-1 · residual CF/browser → STAFF_COMMISSIONING only. See OWNER-ACCEPT-ENTITY-ISOLATION-20261001.

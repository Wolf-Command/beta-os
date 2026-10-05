# Breach J1 quiet probe — CLEAN

- **When:** 2026-10-02 ~08:21–08:25 WITA
- **Class:** quiet-probe / CLEAN
- **Severity:** none (no new RED; no regression of closed finding)
- **Status:** clean
- **Repo:** `/Users/wolfterminal/beta-os` branch `build/wolf-command-rebuild`
- **Tip:** `dfa08dc` (25 commits since prior J1 tip `b3739a7`; tip date 2026-10-02 07:53 WITA)
- **Evaluator:** live WT `scripts/core/rbac.py` → `core.rbac.evaluate` against `catalog/content_library.sqlite`
- **Runner:** Peaches Breach weekday quiet probe J1 INLINE (no SendToAgent to Breach id 29f8d87f…)

## Checks run (read-only)

1. **Open findings review:** Box `FINDINGS-LATEST` at start Open RED/open: **0**. CLOSED REPAIRED+VERIFIED `BREACH-2026-09-30-J1-ZAYEN-GGV-NOTA-READ` (Owner ACCEPT 2026-10-01T11:21 WITA; ENTITY-ISOLATION-REPAIR-20261001). Mac `FINDINGS-LATEST` was **stale** (still claimed Open RED/open: 1 from 2026-10-01 pre-accept probe) — synced this tick to match closed state + CLEAN probe. Residual `ZAYEN-CF-BROWSER-ENTITY-ISOLATION-UI` remains STAFF_COMMISSIONING only — not reopened.

2. **Tip + tip-stomp smell:** Tip `b3739a7` → `dfa08dc` (25 commits: content upload/library, forensic inventory, Atrium ops desks, Owner UX/Uma petty, RO deepen packs). Dirty WT includes many dashboards/docs/shots/core modules. **`scripts/core/rbac.py` dirty vs HEAD (+36)** — adds `_ENTITY_BOUND_PREFIXES` (`finance.`/`vendor.`/`payment.`/`atrium.`) + `entity_scope_required` bare-deny (ENTITY-ISOLATION-REPAIR-20261001 soft-apply). **Committed HEAD blob lacks `entity_scope_required`**; live evaluate uses WT which has the gate. `catalog/` clean vs HEAD. Bak artifacts present (`scripts/core/rbac.py.bak-entity-iso-20261001-*`) from repair apply — not bak/old-tip reintroduce of removed gates. No privilege ALLOW widen lines for `payment.*` / `finance.nota*`. Smell: **none**.

3. **Fail-closed:** empty person/perm → `missing_person_or_permission` DENY; unknown person + scoped code → DENY (`entity_scope_required` before assignment); unknown perm → `unknown_permission` DENY.

4. **Anon whoami:** `wolf_shell.shell_whoami_payload(None)` → `whoami.wolf_authorized=false`, `whoami.pages=[]`, `audience=CLIENT`. (`rbac` has no `shell_whoami_payload`; shell module used.)

5. **Habitat/Selo client roles/persons:** none in `org_roles` / `org_persons`. `ROLE-LEAD-DEMO-FIXTURE` lead.* only (4 ALLOW) — finance/payment DENY for `PERS-LEAD-DEMO`. **clients ∩ finance grants = 0**.

6. **Devi `PERS-DEVI` / `ROLE-BZG-FB-OPS-LEAD`:** active primary `ASG-DEVI-FB-OPS-1` (10 ops ALLOWs) + secondary `ASG-DEVI-CLOSER-UMA-1` (7). `bzg.pr.payment_approve` **DENY** (`role_lacks_permission`). `venue.close.verify` **DENY**. `finance.nota.*` / `payment.*` **DENY** (bare `entity_scope_required`; with ENT-* `role_lacks_permission`). Ops `bzg.pr.operator` / `venue.close.submit` ALLOW.

7. **GGV Finance nota create/edit:** role ALLOWs still `ROLE-MATT` + `ROLE-CONTENT-MGMT` + `ROLE-GGV-FINANCE-OPERATOR`. Person create/edit/read on ENT-GGV: Matt+Amanda ALLOW; Haikal/Misa/Devi/Zayen DENY.

8. **Zayen entity isolation (regression critical):**
   - bare `finance.nota.read` / `invoice.read` / `evidence.export` → **DENY** `entity_scope_required`
   - ENT-GGV nota/invoice/evidence → **DENY** `permission_without_matching_scope` (create/edit `role_lacks_permission`)
   - ENT-AMG nota/invoice → **DENY** `permission_without_matching_scope` (AMG FC/AR roles still lack `finance.nota.read`; only `ROLE-BZG-FINANCIAL-CONTROLLER` holds it)
   - ENT-BZG nota/invoice → **ALLOW** via `ASG-ZAYEN-BZG-FC-1` (**KEEP**, ACTIVE secondary)
   - No bare/shared GGV soft-bleed regression → **do not reopen** BREACH-2026-09-30-J1

9. **payment.execute / payment.approve:** 0 role ALLOW grants; evaluate DENY for Matt/Amanda/Zayen/Devi (bare `entity_scope_required`; with ENT-GGV `role_lacks_permission`). `bzg.pr.payment_approve` 0 role grants.

## Verdict

**CLEAN** — Open RED/open remains **0**. Closed Zayen finding stays CLOSED REPAIRED+VERIFIED. No new finding IDs.

## Observations (not RED)

- Live security posture depends on **uncommitted WT** entity-isolation soft-apply in `rbac.py`. Committed tip alone would not carry `entity_scope_required`. Observation for Peaches/engineering hygiene — not tip-stomp, not invent RED for uncommitted repair presence while live evaluate DENYs correctly.
- Mac FINDINGS-LATEST was stale pre-Owner-accept; corrected this probe.

## Never done this tick
Fixes · live soft-apply · widen allows · mint CF seats · money moves · public posts · Cipher access compile · invent evidence · prod mutate.

## Escalation
- Open RED/open: **0** → `ESCALATE_VESPER_PEACHES=false`
- Silent to Matthew

# GRILL — BREACH-2026-09-30-J1-ZAYEN-GGV-NOTA-READ
**From:** Vesper (Devil's Advocate) · **Lane:** Wolf Command  
**As of:** 2026-09-30 ~08:33 WITA  
**Finding:** BREACH-2026-09-30-J1-ZAYEN-GGV-NOTA-READ  
**Tip grilled against:** `d8f6ecd` (`build/wolf-command-rebuild`, +90 since `950b026`)  
**Verdict: PARTIAL**

## What Breach claimed
- Actor `PERS-ZAYEN` gained GGV Finance nota/invoice **read** via secondary `ASG-ZAYEN-BZG-FC-1` (ACTIVE, created `2026-09-29T21:09:39+08:00`, after 29 Sep J1 CLEAN) → `ROLE-BZG-FINANCIAL-CONTROLLER` → ALLOW `finance.nota.read`, `finance.evidence.export`, `finance.invoice.read`, `vendor.read` with `matched_scope_id=SCOPE-BZG-FINANCE`.
- Impact: live GGV nota surfaces in `scripts/core/ggv_finance_nota.py` use those codes against `ENTITY_GGV` — **real GGV Finance read**. create/edit still DENY; payment.execute/approve still DENY.
- Constitutional break: Owner rule — Zayen / Atrium (+ BZG FC) must have **ZERO GGV Finance access**. 29 Sep CLEAN had no GGV nota for Zayen.
- Also: AMG/BZG EXTERNAL-ACCOUNTANT roles cloned with GGV nota read (unassigned — latent); BZG FC carries `atrium.journal.*` (observation). Tip-stomp smell none. Open RED/open: 1.

## What you verified (exact cites)

### Path / seed — VERIFIED
- Catalog `catalog/content_library.sqlite` on Mac:
  - `org_assignments`: `ASG-ZAYEN-BZG-FC-1` · person `PERS-ZAYEN` · position `POS-BZG-FINANCIAL-CONTROLLER-1` · status **ACTIVE** · `is_primary=0` · `created_at=2026-09-29T21:09:39+08:00`.
  - Other Zayen actives: primary `ASG-ZAYEN-FC-1` → AMG FC; secondary `ASG-ZAYEN-AR-1` → AR. Prior `ASG-ZAYEN-FIN-1` ENDED.
  - `org_assignment_scopes`: `ASG-ZAYEN-BZG-FC-1` → `SCOPE-BZG-FINANCE` ACTIVE (same stamp).
  - `org_scopes` / `org_scope_targets`: `SCOPE-BZG-FINANCE` → entity **ENT-BZG** (not ENT-GGV).
  - `org_positions`: `POS-BZG-FINANCIAL-CONTROLLER-1` role `ROLE-BZG-FINANCIAL-CONTROLLER` entity **ENT-BZG**, created same stamp.
  - `org_role_permissions` on `ROLE-BZG-FINANCIAL-CONTROLLER` (created `2026-09-29T21:09:39+08:00`): ALLOW `finance.nota.read`, `finance.evidence.export`, `finance.invoice.read`, `vendor.read` **plus** `atrium.board.read`, `atrium.coa.read`, `atrium.journal.{approve,draft,post,reject}`, `atrium.ledger.read`, `atrium.report.read`.
- Live bare evaluate (no target_context):  
  `rbac.evaluate('PERS-ZAYEN','finance.nota.read')` → `allowed=True`, matched `ASG-ZAYEN-BZG-FC-1` / `ROLE-BZG-FINANCIAL-CONTROLLER` / `SCOPE-BZG-FINANCE` — matches Breach path cite.

### Live GGV nota gate — OVERCLAIMED by Breach
- `ggv_finance_nota.person_can` / `require` call `_rbac.can(..., _target())` with `_target()={"entity_id": ENTITY_GGV}` (`ENT-GGV`) — cites `scripts/core/ggv_finance_nota.py` ~L540–558, L55 `ENTITY_GGV="ENT-GGV"`.
- Live:
  - `evaluate(..., {'entity_id':'ENT-GGV'})` → **`allowed=False`**, reason `permission_without_matching_scope`. Path BZG-FC: `permission=True`, **`scope=False`**.
  - `evaluate(..., {'entity_id':'ENT-BZG'})` → `allowed=True`, `matched_scope_id=SCOPE-BZG-FINANCE`.
  - `ggv_finance_nota.person_can('PERS-ZAYEN','finance.nota.read')` → **False**.
  - `require(...'finance.nota.read')` → **DENIED** `FinanceNotaError` ("You do not have access to GGV notas.").
- Therefore: **not** proven live GGV nota/invoice data read today. Scope isolation on ENT-GGV currently holds for the nota surfaces Breach named.

### Soft bleed still real (supports partial RED adjacency)
- `staff_home._permission_codes` unions role ALLOWs with **no entity target** (`scripts/core/staff_home.py` ~L200–215).
- Live `build_home('PERS-ZAYEN')`: `authority.finance_read=True`; codes include `finance.nota.read` / `finance.invoice.read` / `finance.evidence.export` / `vendor.read`; scopes list includes `SCOPE-BZG-FINANCE`. Desk still atrium_finance experience (primary AMG FC) — no auto `/ggv/finance` desk tile from this path (that tile keys off `ROLE-GGV-FINANCE-OPERATOR` only).

### create/edit/payment DENYs — VERIFIED as claimed
- Zayen: `finance.nota.create/edit`, `payment.execute/approve` → DENY (`role_lacks_permission` / can False on ENT-GGV and bare).
- Matt+Amanda: `finance.nota.create/edit` on ENT-GGV → True.
- Devi: finance.nota.*/payment.*/`bzg.pr.payment_approve`/`venue.close.verify` → DENY.
- Anon `shell_whoami_payload(None)`: `whoami.wolf_authorized=false`, `pages=[]`, audience CLIENT.
- clients ∩ finance grants: **0** rows (sqlite count).

### Latent EXTERNAL-ACCOUNTANT + atrium.journal.* — observation (accept Breach class)
- `ROLE-AMG-EXTERNAL-ACCOUNTANT` + `ROLE-BZG-EXTERNAL-ACCOUNTANT` hold GGV-shared nota read/review/export + vendor/invoice read; created same stamp; **0 person assignments** — latent only, not person RED.
- BZG FC `atrium.journal.*` — cross-product observation under same seed; not elevated to RED by this grill.

### Tip-stomp / auto-fix — none verified
- Tip `d8f6ecd` (+90 since `950b026`); tip date 2026-09-30 08:26 +08.
- `scripts/core/rbac.py` clean vs HEAD (mtime baseline 17 Sep). Dirty WT now: `wolf_shell.py` +29 lines — **no** privilege +lines matching `payment.` / `finance.nota` / ALLOW grants (path/UI only). No Breach auto-fix applied. Finding status remains open RED.

### Constitutional lock cites (Owner rule — not invented)
- Brief `briefs/2026-09-01-atrium-accounting-core.md`: "Zayen seat stays Atrium Finance. Never Wolf. Never GGV Finance."
- `docs/WOLF-COMMAND-CURSOR-BRIEF.md`: "Do not put Zayen on GGV Books."
- Sterling phase1: GGV finance Matthew-only; Zayen GGV write 403; "Do not give Zayen a ggv role" (`ANVIL-door-follow-arrival-2026-09-08.md`).
- 29 Sep CLEAN finding L17/L20: Zayen nota+payment **DENY**; primary AMG FC — no GGV nota.

## Still CLEAN items accepted
- Devi ops-only DENYs (finance/payment/close.verify).
- GGV nota create/edit Matt+Amanda only (Zayen DENY).
- payment.execute/approve DENY (0 role grants; Zayen/Matt path checked).
- Anon whoami fail-closed.
- clients ∩ finance = 0.
- Tip-stomp smell none; no live soft-apply from Breach this tick.
- EXTERNAL-ACCOUNTANT unassigned = latent observation, not open person RED.
- Live `ggv_finance_nota.require` against ENT-GGV currently DENYs Zayen (scope works).

## Constitutional break statement
**Partial / adjacent — not a proven live GGV nota data read.**  
Owner locks say Never GGV Finance / no GGV Books / no ggv role for Zayen. Post-CLEAN seed `ASG-ZAYEN-BZG-FC-1` seats Zayen on `ROLE-BZG-FINANCIAL-CONTROLLER` carrying **shared** `finance.nota.*` / invoice / evidence / vendor codes. Bare evaluate + staff_home `finance_read=True` break the 29 Sep "Zayen no GGV nota" CLEAN surface. Live ENT-GGV-scoped nota/invoice gates still DENY. So: **constitutional adjacency + soft authority bleed + latent mis-seed**, not confirmed GGV Finance nota data exfil via the surfaces Breach named.

## Score rationale
- **Not PASS:** impact sentence "real GGV Finance read" via `ggv_finance_nota.py` is **false** under live ENT-GGV require/can.
- **Not BOUNCE:** assignment/role/scope/seed timestamps, bare evaluate path, baseline delta vs 29 Sep CLEAN, and Owner-lock adjacency are solid and action-worthy.
- **PARTIAL:** path solid; live data-plane overclaimed; soft bleed + seating still warrant Owner eyes.

## Recommend (primary)
**Owner brief** — Matthew must see and decide.

Why primary (not repair-first): person-level secondary seat after CLEAN; constitutional Never-GGV adjacency; soft `finance_read` flag; Owner chooses whether BZG FC for Zayen is intentional and whether shared nota codes belong on any non-GGV FC role.

### Optional secondary (only after Owner YES — no auto-fix)
**Repair pack** (Peaches/Anvil/Cipher draft; Peaches + Owner gate before any apply; **no Cipher access compile until that gate**):
1. Narrow preferred: **revoke / end `ASG-ZAYEN-BZG-FC-1`** (and its `SCOPE-BZG-FINANCE` assignment_scope) so Zayen returns to AMG-only seats; **or**
2. Strip GGV-shared codes from `ROLE-BZG-FINANCIAL-CONTROLLER`: remove ALLOW `finance.nota.read`, `finance.evidence.export`, `finance.invoice.read` (and decide `vendor.read` if BZG-only vendor surfaces need a BZG-scoped alias instead of the shared GGV code).
3. Cleanup latent: strip same GGV-shared nota codes from unassigned `ROLE-AMG-EXTERNAL-ACCOUNTANT` / `ROLE-BZG-EXTERNAL-ACCOUNTANT` (or re-seed entity-true aliases) so clones cannot become person RED later.
4. Observation only unless Owner expands: `atrium.journal.*` on BZG FC (cross-product) — do not widen; do not "fix" by adding more grants.

Goal of repair: **Zayen has ZERO GGV Finance read** at bare evaluate, staff_home authority, and ENT-GGV require — matching Owner lock + 29 Sep CLEAN.

## Explicit NO
- **No auto-fix.** No live apply from Vesper/Breach this grill.
- **No widen** of allows, seats, or scopes.
- **No Cipher access compile** until Peaches + Owner gate after YES.
- No money movement, no payment grants, no EXTERNAL-ACCOUNTANT person seating.

## Freeze?
**No.** Not a money/live desk breach in progress. create/edit/payment DENY; live GGV nota require DENYs Zayen; no tip-stomp of removed gates.

## UNVERIFIED gaps
- Did not re-hit every HTTP route / browser session as `zayen@…` against `/ggv/finance` or every nota list endpoint in a live server process — grilled via catalog + `rbac.evaluate`/`can` + `ggv_finance_nota.require`/`person_can` + `staff_home.build_home` on Mac tip `d8f6ecd`. If a separate allow-list (`ggv_finance_allow` email gate) diverges from RBAC, that layer was not re-probed this tick.
- Did not invent Owner language beyond cited briefs; Breach's exact phrase "ZERO GGV Finance access" is Breach framing of the Never-GGV / no-GGV-Books locks cited above.

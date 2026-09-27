# Breach J1 quiet probe — CLEAN

- **When:** 2026-09-24 ~08:42 WITA
- **Class:** quiet-probe / CLEAN (not a security finding)
- **Severity:** n/a
- **Status:** CLEAN · complete
- **Repo:** `/Users/wolfterminal/beta-os` branch `build/wolf-command-rebuild`
- **Tip:** `f3ab8f7` (docs after Smart Upload detail P0 `d147739`; prior pin `6602154` Track D)

## Checks run (read-only)

1. **Open findings:** Mac lane `findings/` empty before this note; box had 2026-09-23 incomplete (Mac offline). No prior RED/open security finding.
2. **Tip-stomp smell (recent soft-apply):** `d147739` touches only `scripts/smart_upload.py`, `dashboards/content-2.0.html`, `scripts/tests/test_smart_upload_detail_regression.py`. No allow/rbac/whoami/page_access/finance grant paths in diff. Smell: **none**.
3. **Habitat/Selo client roles/persons:** none in `org_roles` / `org_persons` matching client/habitat/selo role names. `PERS-LEAD-DEMO` is Lead Spine fixture (brand `habitat`) with lead.* only — no finance/payment/publish.
4. **clients ∩ finance grants:** **0** rows.
5. **Devi `PERS-DEVI` / `ROLE-BZG-FB-OPS-LEAD`:** effective 12 ops perms (`bzg.pr.operator`, venue.close read/submit/resolve_exception, venue.receive, evidence.*, work.*). `bzg.pr.payment_approve` **DENY** (`role_lacks_permission`). `venue.close.verify` **DENY** (`role_lacks_permission`). No finance/atlas/money codes granted.
6. **Fail-closed:** empty person/permission → deny; unknown person → deny/unknown_permission. Anon `shell_whoami_payload(None)` → `wolf_authorized=false`, `pages=[]`, audience CLIENT projection only.
7. **Observation (not RED):** `bzg.pr.payment_approve` permission exists but **no role grant** in `org_role_permissions` (Owner also DENY). Deny-by-default everywhere — privilege gap / unwired, not a widen. `venue.close.verify` only on `ROLE-MATT` + `ROLE-BZG-HFB`.

## Never done this tick
Fixes · live soft-apply · widen allows · money/CF/posts · Cipher access compile.

## Escalation
- Open RED/open: **0** → no Vesper escalate.
- Silent to Matthew.

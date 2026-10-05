# ROLE ARCHITECTURE — Uma Blu Captain ⊇ Cashier (reusable)

**Order:** IZA-UMA-CAPTAIN-CASHIER-DAILY-CLOSE-20261002  
**Principle:** People ≠ Roles. No `if Iza`. Future Captains inherit cashier functions by Assignment to `ROLE-BZG-CAPTAIN` without code change after this pack.

## Canonical roles (create/reuse)

| role_id | display_name | Notes |
| --- | --- | --- |
| `ROLE-BZG-CASHIER` | Cashier | Reusable BZG cashier capability bundle |
| `ROLE-BZG-CAPTAIN` | Floor Captain | Uma Blu / BZG Floor Captain; **includes Cashier capability bundle** by seeding the same `org_role_permissions` grants (composition = inheritance without person-specific forks) |
| `ROLE-BZG-CLOSER` | Venue Closing Operator | **Keep.** Devi + future closers. Multi-closer via `venue_closer_roster` ACTIVE rows — do **not** replace Devi |

## Capability inheritance (config, not Iza exception)

```
CASHIER_BUNDLE = {
  venue.close.read,
  venue.close.submit,          # till declare / ESB snapshot / submit path
  evidence.record.read,
  evidence.record.submit,
  work.read, work.update, work.complete
}

ROLE-BZG-CASHIER  ← CASHIER_BUNDLE
ROLE-BZG-CAPTAIN  ← CASHIER_BUNDLE   # Captain may perform Cashier duties
ROLE-BZG-CLOSER   ← existing closer grants (unchanged)
```

No new `if person_id==PERS-IZA`. Captain→Cashier is role-permission composition.

## Positions / Assignments / Scope (Iza)

| id | binds |
| --- | --- |
| `POS-BZG-CAPTAIN-UMA-1` | ROLE-BZG-CAPTAIN · ENT-BZG · BZG-UMA · DEPT-BZG-FB · "Floor Captain · Uma Blu" |
| `ASG-IZA-CAPTAIN-UMA-1` | PERS-IZA → POS-BZG-CAPTAIN-UMA-1 · ACTIVE · is_primary=1 · SCOPE-BZG-UMA |
| `VCR-UMA-2` | venue_closer_roster ACTIVE for PERS-IZA / ASG-IZA-CAPTAIN-UMA-1 (Devi `VCR-UMA-1` untouched) |

**Scope:** ENT-BZG → BZG-UMA only. **DENY** finance, bank, Owner, admin, HR, AMG, GGV (do not grant those perms/scopes).

## Daily Close ACL

- Authorize via **Assignment** (Captain seat + closer roster), not email allowlist.
- UI page gate `serve_beta.py` close_roles must include `ROLE-BZG-CAPTAIN` (reusable) alongside existing CLOSER / FB-OPS / HFB / MATT.
- API remains `rbac.evaluate` on `venue.close.*` via role grants.
- Do **not** bypass unfinished controls (EDC NEEDS CONFIGURATION, variance tolerance empty, OCR soft-warn Owner-skipped).

## Devi

Valid Uma closer. `ASG-DEVI-CLOSER-UMA-1` + `VCR-UMA-1` stay ACTIVE. Multi-closer = multiple roster rows.

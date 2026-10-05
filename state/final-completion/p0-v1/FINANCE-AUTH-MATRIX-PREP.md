# FINANCE AUTH MATRIX — PREP (no invent PASS)

Generated: `2026-09-30T12:23:21+08:00` (WITA) · Peaches · Beta only

## Mechanical checklist (ran without human login)

| Seat | Roles (authority) | Biz chips | Items | Mechanical checks |
|------|-------------------|-----------|-------|-------------------|
| Zayen | ROLE-AMG-FINANCIAL-CONTROLLER, ROLE-AMG-ACCOUNTS-RECEIVABLE, ROLE-BZG-FINANCIAL-CONTROLLER | amg, bzg | /amg/finance, /bzg/finance | {'roles_cover_expected': True, 'hrefs_cover_expected': True, 'biz_cover_expected': True, 'source_assignment_role_scope': True} |
| Amanda | ROLE-CONTENT-MGMT, ROLE-GGV-FINANCE-OPERATOR | ggv | /content-2.0, /ggv/finance | {'roles_cover_expected': True, 'hrefs_cover_expected': True, 'biz_cover_expected': True, 'source_assignment_role_scope': True} |

### Unauth local Beta `:8788`

```
{
  "/amg/finance": {
    "local_beta_unauth": 403
  },
  "/bzg/finance": {
    "local_beta_unauth": 403
  },
  "/ggv/finance": {
    "local_beta_unauth": 403
  },
  "/amg-ops-pack": {
    "local_beta_unauth": 403
  },
  "/bzg": {
    "local_beta_unauth": 403
  },
  "/ggv-ops-pack": {
    "local_beta_unauth": 403
  },
  "/amg-packages-products": {
    "local_beta_unauth": 403
  },
  "/amg-packages": {
    "local_beta_unauth": 403
  }
}
```

Expected unauth: **403** (or CF Access). 200 without auth ≠ PASS.

## Human prove (when they sit down)

See JSON `human_prove_steps_when_seated`. Staff commission on **STAFF-PROVE-QUEUE**. Needs Matt only if Access policy still Owner-gated.

**matrix_pass: null** — do not invent.

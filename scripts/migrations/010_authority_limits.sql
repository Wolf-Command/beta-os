-- Wolf Core Authority Limits (Beta only)
-- HOW MUCH / material conditions. Permission (009) = WHAT. Scope (008) = WHERE.
-- Authority never creates Permission. No admin UI / delegation / dual approval / SoD / real auth.
-- SEEDED LIVE AUTHORITY LIMITS = 0 (test fixtures only, never live IDR staff thresholds).

CREATE TABLE IF NOT EXISTS org_authority_limits (
  authority_limit_id TEXT PRIMARY KEY,
  role_id TEXT NULL REFERENCES org_roles(role_id),
  assignment_id TEXT NULL REFERENCES org_assignments(assignment_id),
  permission_id TEXT NOT NULL REFERENCES org_permissions(permission_id),
  scope_id TEXT NULL REFERENCES org_scopes(scope_id),
  limit_type TEXT NOT NULL CHECK (limit_type IN ('AMOUNT')),
  currency TEXT NULL,
  threshold_value REAL NULL,
  comparison_rule TEXT NOT NULL CHECK (comparison_rule IN ('LTE_INCLUSIVE')),
  effective_from TEXT NOT NULL,
  effective_to TEXT NULL,
  status TEXT NOT NULL CHECK (status IN ('active', 'inactive')),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  CHECK (role_id IS NOT NULL OR assignment_id IS NOT NULL),
  CHECK (
    limit_type != 'AMOUNT'
    OR (currency IS NOT NULL AND threshold_value IS NOT NULL)
  )
);

-- Unique control (assignment-specific). NULL scope/currency coerced for uniqueness.
CREATE UNIQUE INDEX IF NOT EXISTS uq_org_auth_limits_assignment
  ON org_authority_limits (
    assignment_id,
    permission_id,
    IFNULL(scope_id, ''),
    limit_type,
    IFNULL(currency, ''),
    effective_from
  )
  WHERE assignment_id IS NOT NULL;

-- Unique control (role-level when no assignment override row).
CREATE UNIQUE INDEX IF NOT EXISTS uq_org_auth_limits_role
  ON org_authority_limits (
    role_id,
    permission_id,
    IFNULL(scope_id, ''),
    limit_type,
    IFNULL(currency, ''),
    effective_from
  )
  WHERE role_id IS NOT NULL AND assignment_id IS NULL;

CREATE INDEX IF NOT EXISTS idx_org_auth_limits_perm
  ON org_authority_limits(permission_id);
CREATE INDEX IF NOT EXISTS idx_org_auth_limits_asg
  ON org_authority_limits(assignment_id);
CREATE INDEX IF NOT EXISTS idx_org_auth_limits_role
  ON org_authority_limits(role_id);
CREATE INDEX IF NOT EXISTS idx_org_auth_limits_status
  ON org_authority_limits(status);

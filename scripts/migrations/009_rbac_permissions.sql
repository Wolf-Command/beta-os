-- Wolf Core RBAC / Permissions (Beta only)
-- WHAT an Assignment may do. Scope (008) = WHERE.
-- Deny by default. No Authority Limits. No real auth.
-- Legacy table "permissions" (email subject) remains TRANSITIONAL.

CREATE TABLE IF NOT EXISTS org_permissions (
  permission_id TEXT PRIMARY KEY,
  code TEXT NOT NULL UNIQUE,
  resource TEXT NOT NULL,
  action TEXT NOT NULL,
  description TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS org_role_permissions (
  role_id TEXT NOT NULL REFERENCES org_roles(role_id),
  permission_id TEXT NOT NULL REFERENCES org_permissions(permission_id),
  effect TEXT NOT NULL CHECK (effect IN ('ALLOW')),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (role_id, permission_id)
);
CREATE INDEX IF NOT EXISTS idx_org_role_perms_perm ON org_role_permissions(permission_id);

-- Map legacy Content Machine permission strings → canonical codes (TRANSITIONAL)
CREATE TABLE IF NOT EXISTS org_permission_legacy_map (
  legacy_code TEXT PRIMARY KEY,
  permission_id TEXT NOT NULL REFERENCES org_permissions(permission_id),
  note TEXT,
  created_at TEXT NOT NULL
);

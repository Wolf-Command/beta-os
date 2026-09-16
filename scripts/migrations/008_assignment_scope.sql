-- Wolf Core Assignment Scope (Beta only)
-- WHERE an Assignment applies. No RBAC / Authority / real auth.

CREATE TABLE IF NOT EXISTS org_scopes (
  scope_id TEXT PRIMARY KEY,
  scope_type TEXT NOT NULL,
  display_name TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS org_scope_targets (
  scope_id TEXT NOT NULL REFERENCES org_scopes(scope_id),
  target_type TEXT NOT NULL,
  target_id TEXT NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY (scope_id, target_type, target_id)
);
CREATE INDEX IF NOT EXISTS idx_org_scope_targets_target
  ON org_scope_targets(target_type, target_id);

-- Assignment ↔ Scope link. Ending an Assignment must NOT delete Scope or history rows.
CREATE TABLE IF NOT EXISTS org_assignment_scopes (
  assignment_id TEXT NOT NULL REFERENCES org_assignments(assignment_id),
  scope_id TEXT NOT NULL REFERENCES org_scopes(scope_id),
  start_at TEXT NOT NULL,
  end_at TEXT,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (assignment_id, scope_id, start_at)
);
CREATE INDEX IF NOT EXISTS idx_org_asg_scopes_asg ON org_assignment_scopes(assignment_id);
CREATE INDEX IF NOT EXISTS idx_org_asg_scopes_scope ON org_assignment_scopes(scope_id);

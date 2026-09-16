-- Wolf Core Role + Position + Assignment (Beta only)
-- Table prefix org_* avoids collision with LLM routing "role".
-- No Scope / RBAC / Authority in this migration.

CREATE TABLE IF NOT EXISTS org_roles (
  role_id TEXT PRIMARY KEY,
  display_name TEXT NOT NULL,
  department_id TEXT REFERENCES org_departments(department_id),
  role_type TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_org_roles_dept ON org_roles(department_id);

CREATE TABLE IF NOT EXISTS org_positions (
  position_id TEXT PRIMARY KEY,
  role_id TEXT NOT NULL REFERENCES org_roles(role_id),
  entity_id TEXT NOT NULL REFERENCES org_entities(entity_id),
  location_id TEXT REFERENCES org_locations(location_id),
  brand_id TEXT REFERENCES org_brands(brand_id),
  department_id TEXT REFERENCES org_departments(department_id),
  position_label TEXT NOT NULL,
  status TEXT NOT NULL,
  fte REAL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_org_positions_entity ON org_positions(entity_id);
CREATE INDEX IF NOT EXISTS idx_org_positions_role ON org_positions(role_id);

CREATE TABLE IF NOT EXISTS org_assignments (
  assignment_id TEXT PRIMARY KEY,
  person_id TEXT NOT NULL REFERENCES org_persons(person_id),
  position_id TEXT NOT NULL REFERENCES org_positions(position_id),
  start_at TEXT NOT NULL,
  end_at TEXT,
  status TEXT NOT NULL,
  is_primary INTEGER NOT NULL DEFAULT 1 CHECK (is_primary IN (0, 1)),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_org_asg_person ON org_assignments(person_id);
CREATE INDEX IF NOT EXISTS idx_org_asg_position ON org_assignments(position_id);

-- One active primary occupant per position (end_at NULL)
CREATE UNIQUE INDEX IF NOT EXISTS idx_org_asg_one_primary_active
  ON org_assignments(position_id)
  WHERE status = 'ACTIVE' AND is_primary = 1 AND end_at IS NULL;

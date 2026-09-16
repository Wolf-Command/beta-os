-- Wolf Core Organisation Registry (Beta only)
-- Additive. Does not drop Content Machine brands.

CREATE TABLE IF NOT EXISTS org_entities (
  entity_id TEXT PRIMARY KEY,
  legal_name TEXT NOT NULL,
  display_name TEXT NOT NULL,
  entity_type TEXT NOT NULL,
  status TEXT NOT NULL,
  saleable INTEGER NOT NULL CHECK (saleable IN (0, 1)),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS org_brands (
  brand_id TEXT PRIMARY KEY,
  entity_id TEXT NOT NULL REFERENCES org_entities(entity_id),
  display_name TEXT NOT NULL,
  brand_type TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_org_brands_entity ON org_brands(entity_id);

CREATE TABLE IF NOT EXISTS org_locations (
  location_id TEXT PRIMARY KEY,
  entity_id TEXT NOT NULL REFERENCES org_entities(entity_id),
  display_name TEXT NOT NULL,
  location_type TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_org_locations_entity ON org_locations(entity_id);

CREATE TABLE IF NOT EXISTS org_brand_locations (
  brand_id TEXT NOT NULL REFERENCES org_brands(brand_id),
  location_id TEXT NOT NULL REFERENCES org_locations(location_id),
  status TEXT NOT NULL DEFAULT 'ACTIVE',
  created_at TEXT NOT NULL,
  PRIMARY KEY (brand_id, location_id)
);

CREATE TABLE IF NOT EXISTS org_departments (
  department_id TEXT PRIMARY KEY,
  entity_id TEXT REFERENCES org_entities(entity_id),
  ownership TEXT NOT NULL DEFAULT 'ENTITY',
  display_name TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  CHECK (
    (ownership = 'ENTITY' AND entity_id IS NOT NULL)
    OR (ownership = 'SHARED' AND entity_id IS NULL)
  )
);

CREATE INDEX IF NOT EXISTS idx_org_departments_entity ON org_departments(entity_id);

CREATE TABLE IF NOT EXISTS schema_migrations (
  id TEXT PRIMARY KEY,
  applied_at TEXT NOT NULL,
  note TEXT
);

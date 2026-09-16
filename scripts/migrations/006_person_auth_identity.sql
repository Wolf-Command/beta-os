-- Wolf Core Person + Authentication Identity (Beta only)
-- Additive. Does not replace permissions.subject email grants.

CREATE TABLE IF NOT EXISTS org_persons (
  person_id TEXT PRIMARY KEY,
  display_name TEXT NOT NULL,
  legal_name TEXT,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS org_auth_identities (
  auth_identity_id TEXT PRIMARY KEY,
  person_id TEXT NOT NULL REFERENCES org_persons(person_id),
  provider TEXT NOT NULL,
  identifier TEXT NOT NULL,
  status TEXT NOT NULL,
  is_primary INTEGER NOT NULL DEFAULT 1 CHECK (is_primary IN (0, 1)),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  last_verified_at TEXT,
  UNIQUE (provider, identifier)
);

CREATE INDEX IF NOT EXISTS idx_org_auth_person ON org_auth_identities(person_id);
CREATE INDEX IF NOT EXISTS idx_org_auth_identifier ON org_auth_identities(provider, identifier);

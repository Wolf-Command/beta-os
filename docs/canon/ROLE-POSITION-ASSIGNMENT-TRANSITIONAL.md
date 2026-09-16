# Role + Position + Assignment — Transitional Architecture

**Slice:** WOLF CORE — ROLE + POSITION + ASSIGNMENT  
**Scope:** `/Users/wolfterminal/beta-os/` only  
**Date:** 2026-09-16

## Status

| Piece | Status |
| --- | --- |
| Role schema (`org_roles`) | **BUILT** |
| Position schema (`org_positions`) | **BUILT** |
| Assignment schema (`org_assignments`) | **BUILT** |
| Conservative Beta seed (4 people) | **BUILT** |
| Scope | **NOT BUILT** |
| RBAC / Permissions Engine | **NOT BUILT** |
| Authority Limits | **NOT BUILT** |
| Staff Access LIVE | **NO** |

## Naming

Tables and APIs use **org Role** (`org_roles`).  
LLM orchestrator `ROLE_ROUTING` is unrelated.

## Seed policy

- Roles from Identity_Roles.csv IDs preserved (`ROLE-AMG-GM`, `ROLE-BZG-HFB`, `ROLE-GGV-EDIT`, `ROLE-ENG`, `ROLE-MATT`).
- `ROLE-MATT` display = **Owner / Executive** (not the person's name).
- Extra conservative roles for Amanda/Misa Beta content seats: `ROLE-CONTENT-MGMT`, `ROLE-CONTENT-CREW` marked **TBD title**.
- Positions+Assignments only for Matt / Amanda / Haikal / Misa — no invented GM/HFB occupants.
- Shareholder/director is **not** modeled as Position.

## Primary occupancy

Unique index: one `ACTIVE` + `is_primary=1` + `end_at IS NULL` per Position.

## Compatibility

Content Machine permissions remain email-subject based.  
Resolve chain available: development assertion → AuthIdentity → Person → Assignment → Position → org Role.  
Permission decisions are **not** yet Role-based.

# SPEC — Lead Spine v1

Date: 2026-09-18  
Status: OWNER ACCEPTED  
Bound: beta-lead-spine-fixtures  
Canon: `docs/deliveries/CURSOR-MISSION-LEAD-SPINE-2026-09-18.md`

## Object
LEAD is not PERSON, not CUSTOMER, not SALE, not REVENUE.  
Do not insert a lead into `org_persons`. Email/phone are source attributes only and never merge leads.

## Wolf lifecycle
`OPEN`, `ACTIVE`, `PARKED`, `CLOSED` only.  
`CLOSED` is outcome-neutral — not won, not lost, not bought, not verified conversion, not revenue.

## Source stage vocabs (all three remain visible)
1. `CONTENT-DEMAND-5` — `new`, `process`, `followup`, `parked`, `closed`
2. `BAKE-8` — `new`, `contacted`, `qualified`, `viewing`, `offer`, `won`, `not_interested`, `parked`
3. `IMPORT-NOTE-2026-08-21` — `new`, `in process`, `follow-up`, `parked`, `reserved/bought` (words kept verbatim)

Map: new→OPEN; process/followup/contacted/qualified/viewing/offer/in process/follow-up→ACTIVE; parked→PARKED; closed/won/not_interested/reserved/bought→CLOSED. Unmapped source text stays; `wolf_stage` stays null.

## Tables
- `core_leads` — current projection; unique `(entity_id, brand_id, source_system, source_id)`
- `core_lead_events` — append-only; UPDATE/DELETE aborted; observation_key idempotent
- `core_lead_stage_maps` — reference rows only

## Permissions
Codes only (no role grants in migration): `lead.read`, `lead.create`, `lead.event.append`, `lead.assign`.  
`rbac.evaluate` then require winning scope targets include `brand_id`. Entity-wide scope does not pass.

## Conversion
`conversion_status` null | `CLAIMED` | `VERIFIED`. Source `won`/`closed`/`reserved/bought` must not set conversion. Verify requires Core evidence VERIFIED+ACTIVE for that lead.

## Honesty
append_only true · live_import false · external_writes false · hardcoded_people false · closed_implies_conversion false

## Scope
Beta only. Fixtures only. No live lead import. No external writes. No production.

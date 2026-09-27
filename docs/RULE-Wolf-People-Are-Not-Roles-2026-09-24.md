# RULE — Wolf People Are Not Roles — 2026-09-24

**Class:** OWNER LOCK governance rule (architecture permanent).  
**Recorded:** 2026-09-24 ~15:44 WITA · **Armed this file:** 2026-09-24 15:48 WITA  
**Governor:** Peaches · **Executor pack:** cheap/local (no Cursor launch)  
**Beta :**8788 only · **Prod :**8787 sacred · soft head `f3ab8f7` preserve  
**Credit conservation:** ON — no broad refactor from this RULE alone.

## Owner lock (one line)

**People occupy roles; roles do not belong to people.**

## Canonical chain (mandatory)

```
PERSON → ROLE/POSITION → ASSIGNMENT → SCOPE → PERMISSION → AUDIENCE
```

Authorization, workflow ownership, queues, dashboards, escalations, and business rules resolve along this chain. A person's name is never a substitute for Role / Position / Assignment / Permission / Audience.

## Permanent test question (every staff capability)

> If this person resigns tonight, is replaced tomorrow, or their manager reassigns the seat — does the capability, workflow, permission, queue, dashboard, or business rule still work **without engineering**?

If the answer is no, the surface has **INVALID PERSON COUPLING** and must be fixed (P0/P1 in active packs) or registered as succession debt.

## Valid uses of a person name

| Use | Example | Notes |
| --- | --- | --- |
| Identity | `PERS-HAIKAL`, authenticated subject | Who is signed in |
| Greetings / personalisation | "Good morning, Haikal" from `authenticated_person.first_name` | Never authorization |
| Human-facing ownership label | "Assigned to Haikal · Content Director" | Person + role displayed together |
| Audit / history / evidence | "Approved by Haikal at …" | Attribution of what a human did |
| Assignments | Task assignee = person_id | Seat occupancy record |
| Personal task views / notifications | My Needs-You, my mentions | Scoped to authenticated person |
| Comments / approvals actually performed | Comment author, approval decision actor | Evidence of a real act |

## Invalid uses of a person name

Do **not** encode a person's name (or person-named role id, or hard-coded email) when the meaning is their **job**:

- Role definition / role id meant as a job (`ROLE-HAIKAL`, inventing `ROLE-CONTENT-DIRECTOR` from a prompt alone)
- Permission / ACL / capability gate
- Business rule / workflow owner / required approver **class**
- Department / escalation destination
- Dashboard architecture / nav matrix ownership
- Queue ownership when the queue means a seat ("content lead queue" ≠ "Haikal queue" as authority)
- "Send to Matt" when the rule means Owner / Managing Director / Director / authorised approver / shareholder

**Matt included:** never hard-code send-to-Matt / `PERS-MATT` / Matt email where the rule means **Owner / Managing Director / Director / authorised approver / shareholder**. Use Role → Assignment → Permission.

## Personalisation vs authorization

- **OK:** personalisation from authenticated identity (`first_name`, greeting, "your desk").
- **Forbidden:** `if user == Haikal` (or email / `PERS-HAIKAL`) to grant Content Engine, brands, approve, upload, nav, or any permission.
- CE and all staff surfaces: permissions **must** derive from **Assignment → Role** (then Scope → Permission → Audience), not from person id or email hardcodes.

## Haikal role title — RECONCILE NEEDED (do not invent)

> **Superseded for seat occupancy:** see ADDENDUM Owner settled Creative Director below. Do-not-invent rules still stand.

Live Beta `content_library.sqlite` (2026-09-24):

| Fact | Value |
| --- | --- |
| Person | `PERS-HAIKAL` exists |
| Assignment | `ASG-HAIKAL-VE-1` → `POS-VIDEO-EDITOR-1` → `ROLE-GGV-EDIT` (**Video Editor**) ACTIVE |
| Amanda | `ASG-AMANDA-CM-1` → `ROLE-CONTENT-MGMT` (**Content Management (TBD title)**) |
| Creative Director | `ROLE-GGV-CREATIVE-DIRECTOR` = **Creative Director** EXISTS — **no Assignment** |
| Content Crew | `ROLE-CONTENT-CREW` TBD title (Misa seated) |
| `ROLE-MATT` | person-named **id**; `display_name` = **Owner / Executive** |

**Do NOT** create `ROLE-CONTENT-DIRECTOR` or `ROLE-HAIKAL` merely from this prompt or Owner chat suggestion.

CE treats Haikal as content authority; seed Assignment is Video Editor → **P0 succession debt / RECONCILE**.

### Candidates (Owner chooses; no DB mutate in the RULE lock pass)

- **(A)** Assign Haikal to `ROLE-GGV-CREATIVE-DIRECTOR` if that is the org title for content lead (role already exists; seat empty).
- **(B)** Rename TBD `ROLE-CONTENT-MGMT` display to the real org title and re-seat Assignments (Amanda currently occupies this seat — do not silently steal it).
- **(C)** Owner confirms exact Identity_Roles / HR title before any rename or reassignment.

Prefer document the gap; only a clear non-destructive `display_name` fix of an obvious TBD is eligible later — **not** without approved org title evidence. Owner suggested "Content Director"; nearby approved titles are Creative Director, Content Management (TBD), Video Editor — **reconcile, do not invent a fourth role id**.

## Credit conservation

- No broad refactor triggered by this RULE.
- Fix **P0/P1 only** inside **active** packs when touching those surfaces.
- Remainder → Completion Register as open succession debt.
- Do **not** interrupt active Cursor pack `BF-content-engine-haikal-fail-repair-20260924` (pid must stay). Fold check before final Peaches verify if safe: CE authz paths = Assignment→Role, not Haikal-name gates. Haikal-sim identity for commissioning remains VALID.

## Related

- Transitional: `docs/canon/ROLE-POSITION-ASSIGNMENT-TRANSITIONAL.md`
- Master: `docs/canon/WOLF-COMMAND-MASTER-SPECIFICATION.md` (§ Identity / Role / Position / Assignment)
- Audit: `docs/deliveries/AUDIT-Wolf-Person-Name-Coupling-2026-09-24.md`
- CR: `state/completion-register/wolf-people-are-not-roles-20260924.json`
- CE fold: `docs/deliveries/NOTE-CE-Haikal-Repair-People-Are-Not-Roles-Fold-2026-09-24.md`

## ADDENDUM — Owner settled Creative Director (2026-09-24 ~17:34 WITA)

**Owner answer:** Seat Haikal on Creative Director (`ROLE-GGV-CREATIVE-DIRECTOR`).

Reconcile **CLOSED** for the Haikal content-lead seat:

| Id | Result |
| --- | --- |
| Position | `POS-GGV-CREATIVE-DIRECTOR-1` created (ENT-GGV / DEPT-GGV-CONTENT / Creative Director #1 / ACTIVE / fte 1.0) |
| Prior seat | `ASG-HAIKAL-VE-1` → ENDED (history preserved) |
| New seat | `ASG-HAIKAL-CD-1` → `POS-GGV-CREATIVE-DIRECTOR-1` → `ROLE-GGV-CREATIVE-DIRECTOR` ACTIVE `is_primary=1` |
| Amanda | `ROLE-CONTENT-MGMT` / `ASG-AMANDA-CM-1` untouched |
| Not invented | `ROLE-CONTENT-DIRECTOR`, `ROLE-HAIKAL` |

Evidence: `docs/deliveries/NOTE-Haikal-Creative-Director-Assignment-2026-09-24.md`  
CR: `state/completion-register/wolf-people-are-not-roles-20260924.json` (`seat_resolved=true`).

Remaining succession debt (email ACL, person frozensets, etc.) stays on the Completion Register — seat resolve ≠ full People≠Roles cleanup.

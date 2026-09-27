# GROK SPEC — WOLF ROLE-BASED NAVIGATION MATRIX
**Date:** 2026-09-22 ~15:50 WITA (Asia/Makassar UTC+8)  
**Status:** TARGET SPEC  
## Evidence / constraints
- Box-bound audit; live Mac Beta tree not opened. Specs are **TARGET** + evidenced current patterns — do not invent PROVEN/READY maturity.
- One chrome: `#wolfnav` / `sidenav.js`. Never second Boards menu.
- Production `:8787` sacred. Do not rewrite business logic in this doc pack.
- ACTIVE factory Cursor packs: **not killed**.

See also: `docs/deliveries/GROK-SPEC-WOLF-PERMISSIONS-AUDIENCE-2026-09-22.md` and RULE Permissions section.

## Model
`Person → Role → Assignment → Scope → Permission`  
**Do not hard-code people in page logic.** Names below are **fixtures** for design/tests.

Nav shows what you may **navigate**. API/domain enforce access/action. Multi-assignment → **authorised context switcher only** (no silent scope widen).

## Matrix

### Owner / Matt (fixture: mrwolf@ / PERS-MATT)
| | |
|--|--|
| **Landing** | HOME → Empire Pulse (`/wolf` or successor) |
| **Visible primary** | HOME (all) · BUSINESSES (GGV, Atrium/AMG, BZG + drills) · INTELLIGENCE · SYSTEM (Progress, Integrations, Sale Readiness, Factory/Health) |
| **Hidden / not primary** | Legacy specialist boards (still reachable if permitted); raw factory internals |
| **Must never lose** | Progress Owner-only; money/HR/legal widest **via canonical perms**, not UI bypass |
| **Notes** | Widest legitimate projection still through catalog RBAC |

### Devi — BZG F&B Ops Lead (fixture: PERS-DEVI / ROLE-BZG-HFB · SCOPE-BZG-UMA)
| | |
|--|--|
| **Landing** | BZG → Uma Blu → **Today** (`/bzg/uma-blu`) |
| **Visible primary** | HOME: Needs You (Uma-scoped) · BUSINESSES: **BZG only** (Overview + Uma drill) · grammar: Overview/Operations/Issues/(Finance petty if permitted) |
| **Hidden** | Progress · Sale Readiness · Factory · GGV · AMG · Intelligence admin · other BZG venues not in assignment · Entity-wide BZG governance |
| **Denied (API)** | Progress; payment approve; closer submit unless assignment grants; SCOPE-BZG-ENTITY (ended) |
| **Evidence** | `state/build-claims/devi-uma-today-commissioning-2026-09-19.json` (API_AUTH_GATE PENDING_CURSOR — commission separately) |

### Haikal — Content (fixture)
| | |
|--|--|
| **Landing** | Content workspace (content-2.0 / Intelligence→Content) with **authorised brands only** |
| **Visible primary** | HOME Needs You (content tasks) · BUSINESSES brands he is assigned · Content tools |
| **Hidden** | Progress · Finance desks · HR/payroll · Uma ops depth · Sale/Factory · other clients' private workspaces |
| **Notes** | Brand switcher ≠ all brands; Habitat ≠ Selo |

### Amanda — GGV (fixture: amanda@)
| | |
|--|--|
| **Landing** | GGV Overview / management (Lead Spine or GGV mgmt shell) |
| **Visible primary** | HOME Needs You (GGV) · BUSINESSES → **GGV** (+ authorised Atrium pages per access-config sibling) · Customers/Ops/Finance as granted |
| **Hidden** | BZG Uma ops · Progress/Factory · Owner Intelligence · other clients beyond assignment |
| **Sibling evidence** | `scoped_users` atrium-sales/inventory/legal on prod access-config — Beta must mirror via catalog, not hard-code |

### Zayen — Finance (fixture)
| | |
|--|--|
| **Landing** | Finance desk for assigned entities (e.g. atrium-finance) |
| **Visible primary** | HOME Needs You (finance) · BUSINESSES → entities with finance grant · Finance grammar |
| **Hidden** | Content planner · Uma F&B depth · Progress/Factory · Client-private GGV workspaces · payroll detail unless CAN SEE DETAIL |
| **Evidence** | wave1-smoke expects Zayen → `atrium-finance.html` |

### Coral / AMG ops (fixture)
| | |
|--|--|
| **Landing** | Atrium/AMG → **Today / Operations** |
| **Visible primary** | HOME Needs You (AMG) · BUSINESSES → Atrium/AMG only |
| **Hidden** | GGV client interiors · BZG Uma · System · Intelligence admin · shareholder packs |

### Client fixture (e.g. Habitat client)
| | |
|--|--|
| **Landing** | Client project projection |
| **Visible primary** | **Client shell only** — controlled projection |
| **Hidden** | Internal GGV nav · margin · staff chat · other clients · intel · admin · CR debt · audit · unrelated CRM · Owner notes |
| **Notes** | Never inherit operator Boards list |

### Hotel / venue ops (generic)
| | |
|--|--|
| **Landing** | Venue **Today** |
| **Visible** | That venue's Operations/Issues/(Finance if granted) |
| **Hidden** | Corporate governance · other venues · System |

## Multi-assignment
If Devi later gains a second venue: show **context switcher** (Uma | Other) — both must be in Assignment.Scope. Never union-nav that implies entity-wide.

## Test hooks
See Permissions Audience § Test matrix (Matt / Devi / Haikal / client / unauth) — nav **and** direct URL/API.

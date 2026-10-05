# Atrium Ops Four — requirements discovery — 2 Oct 2026

Owner order: recover **real workflows** (not status boards) for Events/Ballroom, Tours/Concierge, Security/CCTV evidence, Maintenance/PM. Honesty UNAVAILABLE pages are forensic findings, not rebuilt software.

**Stamp:** 2026-10-02 ~06:44 WITA · Peaches executor (box) · Mac `forensic-completeness-20261001/`

**Security status:** `ATRIUM-OPS-SECURITY-EVIDENCE-1` is **ALREADY BUILDING** (Cursor `WAITING_CURSOR`, brief `state/build-factory/briefs/BRIEF-ATRIUM-OPS-SECURITY-EVIDENCE-1.md`, run `state/build-factory/runs/ATRIUM-OPS-SECURITY-EVIDENCE-1.json`). Do not re-arm Security.

## Sources searched (quoted)

| Source | Path | What it contributes |
|---|---|---|
| Interview Ledger R4 | `~/beta-os/docs/canon/build-dashboard/Interview_Ledger.csv` Round 4 | AMG: trackable guest requests; housekeeping/room damage; packages; guest journey |
| Interview Ledger R8 | same, Round 8 | Single cross-entity maintenance; asset/barcode; tropical PM; **security/CCTV evidence**; compliance/insurance/disaster; venue commissioning; preventability; risk/promise registers |
| Interview Ledger R9 | same, Round 9 | Canonical customer identity; packages as products; guest portal with concierge and **event planning** |
| Master Spec §13–15 | `~/beta-os/docs/canon/WOLF-COMMAND-MASTER-SPECIFICATION.md` | Guest requests→SLA; daily report includes events; portal: transfers, experiences, concierge, event planning; MSC: one maintenance system, asset IDs, tropical intervals, security incidents/patrols/keys/CCTV registry/evidence timelines, preventability reviews |
| CAP catalog | `~/beta-os/docs/MODEL-C-CAPABILITY-CATALOG.md` | CAP-AMG-03 Packages; CAP-AMG-06 Guest Experience Loop; CAP-MSC-01 Asset & Maintenance Register (MISSING/score 0.05); CAP-MSC-02 Access (BUILT eng, not human-commissioned) |
| Gap register | `~/beta-os/state/completion-register/GAP-REGISTER-20260927.json` | CAP-MSC-01 next_action/blocker=`Register`; dependency kernel already PROVEN |
| Forensic register | `MISSING-FUNCTION-REGISTER.jsonl` | `need.events`, `need.tours`, `need.security`, `need.maintenance`, `need.catering` all MISSING/PARTIAL; NO_V1_SURFACE boards |
| BUSINESS-OPS-AUDIT | forensic dir | Ledger R8: no CCTV desk; incidents.db on V1 not opened as Beta surface; Events/Ballroom no board; Tours/Concierge no surface; Catering PRE-OPENING not events desk |
| V1 incidents | `~/.openclaw/workspace/wolf-system/state/incidents.db` | Schema + 1 near-miss row (BZG slip, open, 2026-05-19) |
| V1 PM schedule | `wolf-system/state/amg-preventive-maintenance.json` | 19 seeded PM tasks (2026-06-18); scripts `amg-preventive-maintenance.py`, `amg-maintenance-create.py` (Cloudbeds RETIRED), `commands/amg/maintenance.py` (Notion/Telegram RETIRED paths) |
| V1 concierge | `wolf-system/scripts/aios_concierge.py` | DISARMED FAQ/escalate simulator; never invent prices; Meta/WATI not wired |
| Beta MSC asset | `beta-os/state/msc-asset/operator-events.jsonl` | EMPTY-MSC-ASSET placeholders only; `inventory_complete` false |
| Beta packages | `beta-os/state/amg-packages/operator-events.jsonl` | EMPTY-AMG-PACKAGES; packages null; yanolja_write false |
| Connections | `CONNECTION-TRUTH-MATRIX.json` | Cloudbeds/ClickUp/Telegram **RETIRED**; CCTV integration absent; Event_Bus ABSENT (technical bus ≠ ballroom) |
| Raw 1500 Q&A | ORIGINAL-REQUIREMENTS-RECONSTRUCTION | **Not found**; 465 rows condensed from 15-line ledger only |

---

## 1. Security / CCTV evidence

### Recovered requirements (quotes)
- Ledger R8: *"security/CCTV evidence"*
- Master Spec §15: *"Security maintains incidents, patrols/checkpoints, keys, visitor/contractor access, CCTV registry/health, evidence timelines and access audit."*
- Master Spec §12 (BZG cash): *"Suspicious events can produce CCTV review windows; Wolf identifies anomalies/evidence, humans investigate."*
- Register `need.security`: MISSING_FROM_BETA; interview R8; no surface.

### Authoritative data — found vs missing
| Found | Missing / do not invent |
|---|---|
| V1 `incidents.db` schema + 1 row (seed/provenance only) | Live CCTV streams, camera inventory, NVR credentials |
| Categories in schema: slip/cut/fire/medical/security/damage/other | Hikvision/other vendor integration |
| CAP-MSC-02 Access eng-built (CF posture) — adjacent, not the evidence desk | Patrol routes, key logs, visitor lists (later slices) |

### Minimum build slice #1 (deterministic workflow — **ALREADY ARMED**)
`incident → time/location → people/asset → evidence ref → optional CCTV timestamp/camera text ref → owner → severity → action → follow-up → close → append-only audit.`  
Not a viewer. Not an honesty board. See BRIEF-ATRIUM-OPS-SECURITY-EVIDENCE-1.

### What NOT to invent
Camera lists, footage URLs, live streams, fake incident volume, Notion/Telegram reopen.

---

## 2. Maintenance / PM

### Recovered requirements (quotes)
- Ledger R8: *"Single cross-entity maintenance system with arm's-length economics; asset/barcode intelligence; tropical-condition PM"*
- Master Spec §15: one Wolf Maintenance for AMG/BZG with entity ownership; permanent Asset ID/barcode; tropical intervals; repair-vs-replace; area scan points
- CAP-MSC-01: *"Asset condition and maintenance tracked."* Gap: blocker=`Register`, inventory empty
- Register `need.maintenance`: MISSING; *"No Beta work orders that match assets screen"*
- V1 script docstring: PM sweep creates due/overdue work; reactive `/maint` logged issues; **rooms never auto-blocked** in PM script

### Authoritative data — found vs missing
| Found | Missing / do not invent |
|---|---|
| `amg-preventive-maintenance.json` 19 tasks with intervals + checklists (seeded 2026-06-18; last_done all seed day → most overdue if clock applied) | Live asset barcode inventory (msc-asset EMPTY) |
| Reactive ticket shape from V1 scripts (room/area + issue + priority keywords) | Cloudbeds PMS events (RETIRED — do not revive) |
| CAP-MSC-01 dependency: core kernel already PROVEN | ClickUp/Notion/Telegram task sinks (RETIRED) |
| Entity arm's-length rule from ledger | Supplier price lists, contractor rates |

### Minimum build slice #1 (deterministic workflow)
**PM due → work order → checklist complete → mark done (reset cycle) → audit**, on Beta sqlite, for **one property (AMG)** first, using the existing 19-task schedule as seed **without inventing new intervals**. Reactive ticket create/list/close as second micro-step in same pack if time allows, else pack 1b.

Not a Kanban status board of fake WOs. Not ClickUp mirror.

### What NOT to invent
New PM cadences beyond the seeded JSON; asset serials; supplier catalogs; room blocks; Cloudbeds writes.

---

## 3. Tours / Concierge

### Recovered requirements (quotes)
- Ledger R4: *"trackable guest requests"*; packages; end-to-end guest journey
- Ledger R9: packages as products; portal with *"concierge and event planning"*
- Master Spec §13: *"Guest requests become trackable service items with SLA/escalation"*
- Master Spec §14 portal: pre-check-in, itinerary, **transfers, experiences**, requests, bills, photos, **concierge**
- CAP-AMG-06 Guest Experience Loop; CAP-AMG-03 Packages as Products
- Register `need.tours`: MISSING; *"Guest requests are not a concierge desk"*
- `aios_concierge.py`: RULE *(1) Never invent prices, availability, policies…*

### Authoritative data — found vs missing
| Found | Missing / do not invent |
|---|---|
| Concierge persona + escalate token pattern (simulate-only) | Tour/experience **prices, packages, supplier menus** |
| EMPTY-AMG-PACKAGES honesty (packages null) | Meta/WATI send path (DISARMED; EXTERNAL) |
| Yanolja Inventory LIVE (vacancy only) — not a tour book | In-house guest directory (UNKNOWN / Bookings denied) |
| Habitat/content “Book a site tour with Matt” is **marketing copy**, not ops | Calendly (BLOCKED_EXTERNAL per E2E) |

### Minimum build slice #1 (deterministic workflow)
**Guest request intake → classify (tour/transfer/amenity/other) → assign owner → SLA clock → status transitions → close with note**, with escalate-to-human when money/booking/complaint.  
Facts library = only vault notes that exist (or explicit UNAVAILABLE). **No auto-reply to guests** until CONCIERGE_ARMED + Owner wire.

Not a FAQ chatbot board. Not package commerce.

### What NOT to invent
Tour prices, dive/surf packages, availability calendars, WhatsApp sends, guest PII from thin `guest-profiles.db`.

---

## 4. Events / Ballroom

### Recovered requirements (quotes)
- Ledger R9 / Master Spec §14: guest portal includes **event planning**
- Master Spec §13 daily report fields include **events**
- Master Spec §5.1 packages include honeymoon/wedding/birthday/engagement/retreat (commercial products — adjacent, not a ballroom BEO system by themselves)
- Register `need.events`: MISSING; no V1/Beta board
- `need.catering`: BZG-CAT PRE-OPENING blank close — **not** an events desk (Pack 9)
- BUSINESS-OPS-AUDIT: *"No board. Catering is a PRE-OPENING registry row, not an events desk."*

### Authoritative data — found vs missing
| Found | Missing / do not invent |
|---|---|
| Constitutional need for event planning on portal + daily “events” field | Ballroom calendar, BEO templates, F&B package rates |
| Catering outlet PRE-OPENING honesty | Menu prices, room hire rates, AV inventory |
| Technical `event-bus.db` / ops-event-bus-1.html | **Not** ballroom — do not reuse as events product |

### Minimum build slice #1 (deterministic workflow)
**Enquiry → hold tentative date/space (name only, capacity UNKNOWN if unknown) → requirements checklist (pax, setup, F&B flag, AV flag) → owner → confirm/cancel → handoff note to ops**, with all money fields **null/UNAVAILABLE** until Owner supplies rate card.

Not a revenue dashboard. Not inventing ballroom SKUs.

### What NOT to invent
Prices, packages, floorplans-as-truth, supplier lists, fake confirmed bookings.

---

## Safest dependency ORDER

| # | Desk | Rationale |
|---|---|---|
| **0 (in flight)** | **Security evidence** | Already armed 2026-10-02. Unblocks incident→evidence→close; feeds cash-theft / preventability later; lowest external-data invention risk (text refs only). |
| **1 (next Cursor)** | **Maintenance / PM** | Seeded 19-task schedule + CAP-MSC-01 Register blocker ready; no CCTV needed; retired ClickUp/Cloudbeds must stay retired — Beta WO store is the point. Guest-impacting PM overlaps later HK but does not wait on Yanolja HK 404s. |
| **2** | **Tours / Concierge (request desk)** | Needs assignable staff + SLA pattern similar to Security/Maint tickets; benefits from identity/guest stay later but slice #1 can run on anonymous/desk-logged requests. Do not wait for packages/prices. |
| **3 (last of four)** | **Events / Ballroom** | Highest invention temptation (rates, BEOs); depends on clearer space/ops handoff and preferably request/identity patterns from Tours; catering outlet still PRE-OPENING. |

**Explicit non-deps for slice #1s:** Xero, Metricool write, Yanolja Bookings write, live CCTV, Cloudbeds/ClickUp/Telegram revive, Intelligence, Exit Report.

**Parallel (not blocking atrium four):** human commission of Haikal/Devi/Zayen/Amanda/Misa packs (see HUMAN-COMMISSION companion).

---

## Register honesty reminder

| id | beta_state | After Security eng-prove (expected) |
|---|---|---|
| need.security | MISSING | → PARTIAL when workflow rows exist; staff_ready stays false |
| need.maintenance | MISSING | stays MISSING until Maint pack lands |
| need.tours | MISSING | stays MISSING |
| need.events | MISSING | stays MISSING |
| need.catering | PARTIAL PRE-OPENING | unchanged — not Events |


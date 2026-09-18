# WOLF OVERNIGHT BUILD AUDIT — 2026-09-19

Owner: Matt Goss  
Mission: OWNER OVERNIGHT RELEASE — 18 September 2026  
Auditor: Peaches  
Zone: Asia/Makassar (WITA)

## 1. EXECUTIVE SUMMARY

Overnight the factory finished five Beta lanes without touching Production and without changing Model C SYSTEM.

What materially changed:

- Progress now projects SYSTEM from the canonical ledger on every read (25.3%). A mismatch shows SCORING PROJECTION STALE instead of a false percent.
- Owner cockpit top card is WOLF TRANSFORM with one SYSTEM headline and five Not scored yet dials.
- Empire GGV / AMG / BZG surfaces are honest ESTIMATED labels, not fake overall progress.
- Uma Blu gained a petty-cash surface that refuses to invent an opening float (OPENING BALANCE REQUIRED / NOT_FOUND).
- Uma History and Issues now read the existing audit spine. Live History is empty until new transitions. Issues stays mostly quiet and labels Example rows.

SYSTEM stayed 19.45 / 77 = 25.3%. No capability maturity promotions overnight. Model E still unscored.

Saturday stall: History/Issues Cursor died ~00:21 with no EXIT. Build-factory watch does not run Saturday, so the lane sat until ~06:49 relaunch. That is a real factory gap, not theatre.

## 2. OWNER COCKPIT

Usable now on Beta `http://127.0.0.1:8788/progress` (200):

- WOLF TRANSFORM card
- SYSTEM — computed 25.3% — Technical capability built & proven
- Operating Adoption / Data Measurement / Founder Independence / Financial Control / Sale Readiness — Not scored yet
- Needs you / Waiting on others / Policy / Owner pulse / Build Factory sections remain
- Empire nav: Empire · GGV · AMG · BZG

Not overall transformation: SYSTEM is technical capability only.

## 3. BZG / UMA BLU

Routes proven 200 on Beta:

- `/bzg`
- `/bzg/uma-blu`
- `/bzg/uma-blu/bills`
- `/bzg/uma-blu/issues`
- `/bzg/uma-blu/petty`
- `/api/bzg/uma-blu/history`
- `/api/bzg/uma-blu/issues`
- Daily Close still the existing `/uma-blu-close` engine

Genuinely operational vs built:

- PR → bill lifecycle UI and honesty flags: BUILT (payment execution NOT_BUILT; no invented authority limits)
- Petty cash page: BUILT with float NOT_FOUND / OPENING BALANCE REQUIRED — usable as a missing-policy surface, not a live float ledger
- History: read model BUILT; live catalog empty until new events
- Issues: read model BUILT; quiet when clean; Example POLICY_REQUIRED may appear with `example: true`

Not operational for staff yet: Devi not in org_persons; opening float unknown; Telegram/Alchemist remains the real floor loop until commissioning.

## 4. INTELLIGENCE

No new overnight integration of AKR / Decision Memory into Owner or BZG surfaces (P5 parked when morning audit became due).

Already proven earlier 18 Sep (unchanged overnight):

- Authorised Knowledge Resolver
- Decision Memory
- Knowledge resolution composer

## 5. MODEL C

Starting audited SYSTEM: **25.3%** (19.45 / 77)

Ending audited SYSTEM: **25.3%** (19.45 / 77)

Capability movements overnight: **none**

No ledger edits. No credit-table edits. No CAP promotions.

## 6. MODEL E

Operating Adoption — Not scored yet  
Data / Measurement — Not scored yet  
Founder Independence — Not scored yet  
Financial Control — Not scored yet  
Sale Readiness — Not scored yet  

No scoring rules approved overnight. Left unscored.

## 7. FACTORY

| Lane | Attempts | Retries | Block / recovery | Commit | Review | Runtime proof |
|---|---|---|---|---|---|---|
| P0 Dashboard truth | 1 | 0 | none | `eb79710` | PASS | `/progress` 200; truth tests 50/0; SYSTEM 25.3 |
| P1 Owner cockpit UX | 1 | 0 | none | `17bc052` | PASS | `/progress` 200; truth 58+/0 |
| P2 Empire surfaces | 1 | 0 | none | `75fd2d4` | PASS | `/progress` 200; ESTIMATED labels |
| P3 Uma petty + Today | 1 | 1 relaunch (dead child, no EXIT) | recovered 23:51 | `99d0970` | PASS | `/bzg/uma-blu/petty` 200; float NOT_FOUND |
| P4 History + Issues | 1 | 1 relaunch after Saturday stall | recovered 06:49 | `e797592` | PASS | history API 200; issues 200; ops 24/0; petty 52/0 |
| P5 Decision Memory on surfaces | 0 | — | PARKED for morning audit | — | — | — |
| P6 Model C evidence remediation | 0 | — | PARKED for morning audit | — | — | — |

Docs/review commits also landed: `d0feab9`, `5be4d10`, `af3a38d`, `c07cf38`, `b333aa3`, `071545e`.

## 8. HUMAN BLOCKERS

### NEEDS MATT

- (none required to keep safe lanes moving; morning decision only if he wants P5/P6 continued today)

### NEEDS STAFF

- Devi (Uma Blu ops) not in Beta `org_persons` — human commissioning of Uma console blocked
- Floor still runs Telegram + Alchemist until staff prove the console

### NEEDS POLICY

- Petty-cash opening float / cash-box identity — OPENING BALANCE REQUIRED (NOT_FOUND)
- Monetary authority limits for payment steps — POLICY_REQUIRED (do not invent)
- Variance threshold for daily close — do not invent

### NEEDS EXTERNAL ACCESS

- none for the overnight Beta lanes

## 9. PRODUCTION SAFETY

Production / external mutations overnight: **NONE**

Explicitly untouched: Production DB, DNS, Cloudflare, secrets, customer/supplier messages, payments, bank writes, ESB writes, Yanolja, Metricool, Klaviyo, Sheets, ClickUp, Telegram ops, email sends, purchases/contracts.

Beta :8788 only. Production `:8787/wolf.html` read-only 200.

(Earlier same-day Depo sheet correction was before this overnight release and is not part of overnight mutations.)

## 10. DIRTY WIP

Preserved unstaged throughout:

- `scripts/migrations/migrate_phase2_6_team_readiness.py`
- `scripts/phase26_team.py`
- `scripts/skills/__init__.py`
- `scripts/wolf_intelligence.py`

No `git add .`. No blind reset.

## 11. RED TEAM

What could still be wrong despite green tests:

- Static HTML curl of `/progress` still contains template stale/legacy strings; the live number is API/read-model driven — do not trust raw HTML grep alone.
- Example POLICY_REQUIRED rows can look like real Issues if the UI fails to show the Example label.
- Live History emptiness can be misread as “broken” instead of “no events yet”.
- Saturday factory watch gap will stall again on weekend Cursor deaths unless a weekend advance path exists.
- Uma console is Beta software, not proven staff-operated adoption.

## 12. TOMORROW'S BEST NEXT MOVES

Ranked by business value / founder-independence:

1. **Commission Uma Blu Today with one real operator path** — put Devi (or named closer) in org_persons, keep float as OPENING BALANCE REQUIRED until Zayen/policy supplies it, and prove one real PR attention loop without Telegram. Highest independence impact.
2. **Wire Decision Memory / AKR “why blocked / what did we decide” onto Needs you and Uma Issues** — explainable provenance only, no chat agent. Cuts Matt interpretation load.
3. **Add a weekend factory advance path** — Saturday/Sunday recover dead WAITING_CURSOR children without Matt typing status. Stops the overnight disappearance class that hit P4.

Do not start Production migration. Do not invent float or authority limits. Do not score Model E yet.

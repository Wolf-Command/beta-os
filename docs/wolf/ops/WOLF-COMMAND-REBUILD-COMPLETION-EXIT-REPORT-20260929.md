# WOLF COMMAND — REBUILD COMPLETION & EXIT REPORT

**As of:** 2026-09-29T22:45:06+08:00 (WITA)  
**Author:** Peaches (Mac executor) from canonical pack evidence  
**Branches:** beta-os `build/wolf-command-rebuild` @ `dcc80e98c5fb` · atrium-finance `wolf/beta-mount-20260928` @ `1ecfc3cef3d2`  
**Ports:** Prod `:8787` pid **15975** READ-ONLY untouched · Beta `:8788` · Sidecar `:8790`  
**Flags (locked):** `staff_ready=false` · `human_commissioned=false` · **No push** · **Exit gate LOCKED — no new major build packs**

## Scoring canon (locked)

| Label | Score | Meaning |
| --- | ---: | --- |
| ABSENT | 0.00 | Not present |
| SPECIFIED | 0.05 | Specified / inventoried only |
| BUILT | 0.25 | Implemented on Beta; not fully proved |
| PROVEN | 0.80 | Tests + shots + Peaches verify on Beta |
| READY | 1.00 | Staff-ready **and** human-commissioned for live ops |

**This report never awards READY for staff or human commissioning.** Those remain false by Owner lock.

---

## 1) SYSTEM COMPLETION

Rebuild of **Finance Core + BZG multi-outlet + non-HR V1 retirement** on Beta is **PROVEN (0.80)** for the Owner-ordered sprint map. Not READY (1.00) — no go-live / staff_ready / human_commissioned claim.

### Sprint map (executed 2026-09-29 WITA)

| Pack | Status | Beta SHA / notes | Tests (Peaches re-run) |
| --- | --- | --- | --- |
| CORE-ENT-1 | PASS_VERIFIED | entity isolation; Zayen BZG FC; GGV 403; Ext Acct unseated | ent1 49/0 · sod1 69/0 |
| BZG-OUTLET-1 | PASS_VERIFIED | `org_outlet_registry` 7 rows; Uma OPEN; others PRE-OPENING | outlet1 82/0 |
| CORE-BOOKS-1 | PASS_VERIFIED | separate SQLite files AMG/BZG/GGV; empty shells BZG+GGV | books1 64/0 |
| BZG-XOUTLET-1 | PASS_VERIFIED | cross-outlet foundations; nullable `outlet_id` hooks | xoutlet 89/0 |
| V1-SWEEP-1 | PASS_VERIFIED | 23-id register; safe Beta redirects; HR deferred; RO warehouses intact | v1sweep 67/0 |
| Checkpoint pre-BOOKS | local commits | beta `9e0da04` · atrium `dda9567` | — |
| Latest sprint tip | local commits | beta `dcc80e98c5fb` · atrium `1ecfc3cef3d2` | full suite below |

### Full verification stamp (this report)

| Suite | pass | fail |
| --- | ---: | ---: |
| test_core_ent1_20260929.py | 49 | 0 |
| test_bzg_outlet1_20260929.py | 82 | 0 |
| test_core_books1_20260929.py | 64 | 0 |
| test_bzg_xoutlet1_20260929.py | 89 | 0 |
| test_v1_sweep1_20260929.py | 67 | 0 |
| test_atrium_sod1_20260929.py | 69 | 0 |
| test_staff_access_20260928.py | 275 | 0 (earlier in chain; Zayen BZG allow / GGV deny intact) |

**System completion score:** **0.80 PROVEN** (Beta engineering). Remaining to READY requires human commissioning + staff_ready Owner flips (out of scope).

### Design decisions locked in evidence

1. **ONE FINANCE PRODUCT · THREE ENTITY CONFIGS** — RULE `docs/RULE-One-Finance-Product-Three-Entity-Configs-2026-09-29.md`
2. **Books isolation:** separate SQLite files under `~/atrium-finance/data/beta/` (`atrium.sqlite`, `atrium-bzg.sqlite`, `atrium-ggv.sqlite`)
3. **Hierarchy:** ENT-BZG → OUTLET → nullable cost/revenue centres; Pool Bar = `OU-BZG-RAIN-POOL` under `BZG-RAIN`
4. **Authority:** Zayen AMG+BZG / GGV 403; Amanda GGV-only; Ext Acct shells unseated

---

## 2) STAFF READY

**Score: 0.00 ABSENT (as operating claim) / contract false.**

| Claim | Value | Evidence |
| --- | --- | --- |
| `staff_ready` | **false** | All pack RESULTS + ARM/VERIFY JSON + honesty stamps on desks |
| Finance desks | Engineering shells only | AMG live books (Beta); BZG/GGV empty shells; no READY banners |
| BZG outlets | Registry + foundations | Uma OPEN config; Rain/Pool PRE-OPENING; no fake ops metrics |

**Do not treat System PROVEN as Staff READY.** Owner must flip separately after human commissioning.

---

## 3) HUMAN COMMISSIONED

**Score: 0.00 ABSENT (as operating claim) / contract false.**

| Claim | Value | Evidence |
| --- | --- | --- |
| `human_commissioned` | **false** | Pack contracts; `/ops/v1-status` honesty box; finance desk stamps |
| Human commissioning | Continues independently | Not blocked by this exit; not completed by this sprint |

Seats exist (Zayen FC AMG+BZG, Amanda GGV, Devi/Hariyanto F&B scopes, Zenitalfathan AP) but **commissioning gate remains false**.

---

## 4) OPERATING ADOPTION

**Score: ~0.25 BUILT → partial PROVEN for engineering paths; not operating adoption READY.**

| Area | Score | Note |
| --- | ---: | --- |
| AMG Beta books + SoD | 0.80 | ATRIUM-SOD-1C proved; COMM1 intact |
| BZG finance books | 0.25 | Empty shell open; zero journals/accounts |
| GGV finance books | 0.25 | Empty shell open; Beta invoice/nota path exists separately |
| BZG outlet registry | 0.80 | 7 rows + hierarchy scopes proved |
| Cross-outlet foundations | 0.25–0.80 | Hooks proved; vendors/closes empty by design |
| Staff daily use | 0.05–0.25 | Not staff_ready; human commissioning independent |

No invented operating metrics. Rainforest/Pool Bar remain PRE-OPENING.

---

## 5) V1 RETIREMENT (ex-HR)

**Score: 0.80 PROVEN for status register + safe Beta redirects; MOUNTED RO remain by design (not cut over).**

Register: `state/finance-core-sprint/V1-STATUS-REGISTER-20260929.json` · surface `/ops/v1-status`

| Class | Count | Disposition |
| --- | ---: | --- |
| SUPERSEDED | 3 | Beta redirects where safe (e.g. `/atrium-finance*` → `/amg/finance`) |
| HISTORICAL ONLY | 5 | Marked historical; no go-live |
| MOUNTED READ-ONLY | 6 | **Left mounted RO** (ESB, alchemist, V1 GGV money, recipes, …) — **no destructive SoR cutover** |
| REBUILT IN WOLF | 4 | Beta path confirmed |
| HR-DEFERRED | 1 | **HR stays V1** |
| BLOCKED | 2 | Documented blockers |
| DISCOVER-NEEDED | 2 | Documented |

**HR:** explicitly **DEFERRED** — not retired.

---

## Master remaining-work register

| ID | Work | Owner | Priority | Blocks READY? |
| --- | --- | --- | --- | --- |
| RW-HR-1 | HR V1 → Wolf rebuild (deferred) | Matt / HR lane | Later | Yes for HR-ready |
| RW-COMM-1 | Human commissioning loops (Zayen/Amanda/Devi/…) | Matt + Peaches commissioning | Active independent | Yes for human_commissioned |
| RW-STAFF-1 | Owner flip `staff_ready` after commissioning evidence | Matt | After RW-COMM-1 | Yes for staff_ready |
| RW-BZG-BOOKS-2 | Seed real BZG COA / journals when Owner authorises (no fake) | Finance / Zayen | When authorised | Partial |
| RW-GGV-BOOKS-2 | GGV books depth beyond empty shell | Amanda / Finance | When authorised | Partial |
| RW-OUTLET-GO | Rainforest/Pool Bar commissioning → status upgrade | F&B / Matt | Pre-open timeline | Ops |
| RW-CENTRES | Populate cost/revenue centres (hooks exist, null today) | Finance | Later | Reporting |
| RW-RO-CUT | Destructive cutover of MOUNTED RO SoR (ESB/alchemist/…) | **Matt only** | When authorised | Data migration |
| RW-BLOCKED | Resolve V1 register BLOCKED + DISCOVER-NEEDED ids | Peaches discovery | As needed | Clarity |
| RW-PROD | Prod deploy of Finance Core (not this exit) | Matt | After READY | Prod |
| RW-PUSH | Remote push of rebuild branch (not this exit) | Matt | When authorised | Sync |

### Critical path to operating READY (not started by this exit)

1. Human commissioning evidence per seat (independent track)  
2. Owner flips `human_commissioned` / `staff_ready` with evidence  
3. Optional: real BZG/GGV COA + outlet go-lives without invented numbers  
4. Matt-authorised SoR cutovers for remaining MOUNTED RO  
5. Prod deploy decision (separate)

### Rebuild finish list (this exit — DONE)

- [x] CORE-ENT-1 entity isolation + Zayen BZG FC + GGV deny  
- [x] BZG-OUTLET-1 canonical registry + hierarchy scopes  
- [x] CORE-BOOKS-1 separate entity books files + empty shells  
- [x] BZG-XOUTLET-1 cross-outlet foundations  
- [x] V1-SWEEP-1 non-HR register + safe Beta redirects  
- [x] Full focused regression green on Beta  
- [x] Local checkpoints committed (no push)  
- [x] Prod `:8787` untouched  
- [x] Exit gate locked — **no new major build packs**

---

## Exit gate

**LOCKED.** Factory IDLE reason: `EXIT_GATE_LOCKED_AFTER_REBUILD_COMPLETION_REPORT`.  
Do **not** arm HEADCHEF, random breadth, or new major feature packs from this exit.  
Bug fixes + human commissioning OK.

**Evidence roots:** `docs/wolf/ops/{CORE-ENT,BZG-OUTLET,CORE-BOOKS,BZG-XOUTLET,V1-SWEEP}-1-RESULT.md` · `state/finance-core-sprint/*-PEACHES-VERIFY.json` · `state/rebuild-exit/`

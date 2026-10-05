# TRANSFER-LEARNING-SPEC — Beta Owner Learning Desk (P0)

Generated: 2026-09-30T11:04:38+08:00 (WITA)  
Owner: **Matthew only** · Executor: Peaches  
Constraint: **TTC paper only** · nothing trades · `staff_ready=false` · never claim REBUILT+PROVEN · no prod :8787 · no Exit Report

## Purpose

Restore Owner Learning Desk as a first-class Beta Owner surface. V1 `learning.html` is recoverable. Migration stays **PARTIAL** until human prove.

## V1 inventory (source of truth)

| Asset | Path | Notes |
|-------|------|-------|
| Board | `~/.openclaw/workspace/wolf-system/dashboards/learning.html` | live badge; Matthew only |
| JS | `dashboards/assets/learning-desk.js` | cockpit renderer |
| API | V1 `/api/learning` | tracks + lessons |
| State | `state/learning-desk/` | tracks.json · inbox.jsonl · ttc-learn-base/ digests |
| Tracks | ttc-trading · acquisition-sales · dan-martell | TTC paper; drop w/o track refused |
| Distinct | Beta `/intel/learning` | Intel Learning Policy — **not** this desk |

## Beta target (Owner-only)

| Item | Value |
|------|-------|
| Canonical route | `/owner/learning` |
| HTML | `~/beta-os/dashboards/owner-learning-1.html` |
| Legacy aliases | `/learning`, `/learning.html`, `/dashboards/learning.html` → `/owner/learning` |
| IA | HOME "Learning (Owner)" key=`owner_learning` |
| Audience | Owner / Matthew only |
| migration_state | **PARTIAL** |
| staff_ready | **false** |
| TTC / trading | PAPER ONLY — nothing trades |

## Transfer steps

1. Ship `owner-learning-1.html` honesty strip (PARTIAL · paper TTC · V1 SoT paths).
2. Alias legacy learning URLs → `/owner/learning` (was 404 on Beta).
3. IA HOME + crumbs + parent under Empire (mirror Trading/Fitness/Travel).
4. Do **not** re-wire `/api/learning` this pass — honest empty / stamp only.
5. Human prove: Matthew opens `/owner/learning`; confirms not confused with `/intel/learning`.

## Non-goals

- Live broker / TTC execution
- Rebuilding full learning-desk.js cockpit on Beta
- Merging with Intel Learning Policy board
- Claiming REBUILT+PROVEN or staff_ready

## Honesty / provenance

- V1 learning desk state remains SoT until Beta prove + optional read-only mirror.
- TTC overlaps Trading transfer — paper program brief stays shared provenance.

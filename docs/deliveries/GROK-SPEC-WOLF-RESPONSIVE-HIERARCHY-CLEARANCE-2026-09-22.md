# GROK SPEC — Responsive + Hierarchical + Clearance-Aware Shell
**Date:** 2026-09-22 ~16:46 WITA  
**Status:** OWNER CORRECTION · NON-NEGOTIABLE · fold into Global Nav V1 now  
**Refs:** RULE-Wolf-Global-Navigation-Design-System-2026-09-22 · PERMISSIONS-AUDIENCE · GLOBAL-SHELL · ROLE-NAV-MATRIX · PAGE-TYPES · TARGET-IA

## Default
RESPONSIVE EVERYWHERE unless a surface is explicitly classified desktop-only with a documented operational reason.

## One responsive shell
| Viewport | Expectation |
|----------|-------------|
| Desktop | Persistent/expandable side nav; top context/header; breadcrumbs; page actions; contextual subnav |
| Tablet | Adaptive mid layout; touch-safe |
| Mobile | Compact top bar; menu/drawer; stacked cards/lists; touch-safe; no horizontal table dependency; no clipped nav; no tiny desktop controls; no browser zoom required |

Do **not** build separate mobile and desktop products unless genuinely necessary.

## Direction (every page)
- **UP** — parent level  
- **BACK** — previous logical context  
- **FORWARD / NEXT** — next relevant item/workflow step when product warrants and user is authorised  
- **HOME / ROOT** — authorised landing  

Browser-back may work; Wolf must provide its own predictable model.

## Breadcrumbs
Hierarchy-aware above object/detail. Examples: Empire → BZG → Uma Blu → Purchasing → PR-1385. Mobile may collapse intelligently; parent context always known.

## Clearance
Nav generated from Person → Role → Assignment → Scope → Permission → Audience.  
No hard-coded `if Devi` / `if Matt` in page logic.

Show only destinations the identity may legitimately navigate (Owner widest; Devi F&B; Haikal content; Client projection only).

## Security
**NAVIGATION VISIBILITY IS NOT ACCESS CONTROL.**  
Hidden link ≠ denied access. Direct route/API must enforce same permissions. Test both: not in nav **and** typed URL/API fails closed.

## Context switcher
Only for multiple legitimate assignments. Never show unauthorised contexts.

## Tables / detail / workflow
- Desktop table → mobile cards/list rows (key fields, status, action, drilldown).  
- Detail: Back to list · parent context · Previous/Next only when both authorised (no existence leak).  
- Workflow stage rail: honest state only.

## Search
In shell; same clearance; no metadata leakage; land in authorised context with back preserved.

## Route consolidation
Old routes temporary OK; canonical nav → shell route; safe redirects; unmigrated = CR debt; no dead-end without path back into Wolf.

## Acceptance bars
**Staff-ready:** desktop · mobile · role-aware nav · direct RBAC · parent/back/up · no dead-end · no eng language · understandable path.  
**Owner-ready:** Empire → business → site/venue → function → workspace → object and back — no remembered URLs.

## V1 READY notify contents
Desktop screenshots · mobile screenshots · role matrix proof · URL/API denial proof · breadcrumb/back/up proof · context-switch proof.

## Factory
Continue Wave order: shell/tokens → Empire → BZG/Uma → GGV → AMG → Intelligence → System → remaining.  
Empire HOME review and later waves MUST prove against this bar (register debt if partial; do not invent PROVEN).

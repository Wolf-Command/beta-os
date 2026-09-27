# RULE — Wolf Global Navigation & Design System
**Effective:** 2026-09-22 ~15:50 WITA  
**Owner:** Matthew Goss / Wolf Command  
**Applies to:** Beta `:8788` dashboard surfaces (and future prod only after explicit promote)

## Standing
1. **One chrome:** `#wolfnav` owned by `sidenav.js` (or in-place successor). **Never** a second Boards menu.  
2. **NEW dashboard surfaces MUST use** global shell + Target IA + page-type attrs + shared tokens.  
3. **Unmigrated routes = design-system debt** (track; do not pretend done).  
4. **Factory register gate:** Cursor/Build Factory packs that add HTML/UI must cite this RULE + Permissions Audience spec; reject packs that invent parallel nav or hard-code people into page logic.  
5. **Production `:8787` sacred** — no drive-by mutation from nav migration.  
6. **Do not invent PROVEN/READY** maturity in UI copy.  
7. **Do not kill ACTIVE factory packs** to “make room” for nav work — schedule additive slices.

## IA (summary)
Primary nav conceptual: **HOME** · **BUSINESSES** (GGV, Atrium/AMG, BZG) · **INTELLIGENCE** · **SYSTEM**.  
Org hierarchy: GROUP → ENTITY → SITE → BU/VENUE → DEPT → WORKSPACE → OBJECT. Brand is contextual.

## Page types
`DASHBOARD | WORKSPACE | DETAIL | MANAGEMENT | SYSTEM` — see `docs/deliveries/GROK-SPEC-WOLF-PAGE-TYPES-2026-09-22.md`.

## Permissions (standing)
Full normative text: `docs/deliveries/GROK-SPEC-WOLF-PERMISSIONS-AUDIENCE-2026-09-22.md`.

**Must hold:**
- Nav never sole security boundary; **API auth canonical**; Hidden menu ≠ permission.  
- Four layers: CAN SEE · CAN ACT · CAN SEE DETAIL · CAN SEE ACROSS SCOPE.  
- Person→Role→Assignment→Scope→Permission — no hard-coded people in page logic.  
- Client projections controlled; never inherit internal operator nav or leak sensitive classes.  
- Owner widest projection still via canonical perms (no UI bypass).  
- Search RBAC — no existence/metadata leak.  
- Intelligence inherits requester perms — not a side door.  
- Export / Client / Buyer Mode separately permissioned.  
- **SHELL · API · DOMAIN — all three agree.**

## Spec index (2026-09-22)
- `docs/deliveries/GROK-AUDIT-WOLF-ROUTE-MAP-2026-09-22.md`  
- `docs/deliveries/GROK-SPEC-WOLF-TARGET-IA-2026-09-22.md`  
- `docs/deliveries/GROK-SPEC-WOLF-ROLE-NAV-MATRIX-2026-09-22.md`  
- `docs/deliveries/GROK-SPEC-WOLF-PAGE-TYPES-2026-09-22.md`  
- `docs/deliveries/GROK-SPEC-WOLF-GLOBAL-SHELL-2026-09-22.md`  
- `docs/deliveries/GROK-SPEC-WOLF-DESIGN-SYSTEM-MAP-2026-09-22.md`  
- `docs/deliveries/GROK-SPEC-WOLF-PERMISSIONS-AUDIENCE-2026-09-22.md`  
- `docs/deliveries/GROK-PLAN-WOLF-ROUTE-MERGE-RETIRE-REDIRECT-2026-09-22.md`  
- `docs/deliveries/GROK-PLAN-WOLF-NAV-MIGRATION-ORDER-2026-09-22.md`  

## Sync
Box mirror path used when Mac Shell unavailable: `/workspace/docs/...`.  
Copy to `/Users/wolfterminal/beta-os/docs/...` via Mac-routed executor or MAC-APPLY — do not claim live Mac write without prove.

## Responsive + Hierarchical + Clearance (Owner correction 22 Sep)

**Fold into V1 now — not a later mobile cleanup.**

1. **Default responsive everywhere** (desktop / tablet / mobile) unless a surface is explicitly classified desktop-only with a valid operational reason.
2. **One responsive shell** — desktop: side nav + header + breadcrumbs + actions + subnav; mobile: compact top bar + drawer + touch-safe + stacked cards — no clipped nav, no tiny controls, no browser-zoom required. Not separate products.
3. **Direction on every page:** UP (parent) · BACK (logical prior) · FORWARD/NEXT (workflow/list where safe) · HOME/ROOT (authorised landing). Browser-back may work; Wolf must not depend on it.
4. **Breadcrumbs** hierarchy-aware above object/detail; mobile may collapse but parent context always known.
5. **Clearance-driven nav** from Person → Role → Assignment → Scope → Permission → Audience. No hard-coded people in page logic.
6. **Show only navigable destinations** for that identity (Matt widest; Devi BZG F&B; Haikal content; Client projection only).
7. **Hidden ≠ permission.** Direct URL/API must fail closed even when nav hides the link.
8. **Context switcher** only for authorised multi-assignments.
9. **Tables:** desktop table → mobile cards/list rows (same data, different presentation).
10. **Detail:** Back to list + parent context; Previous/Next only when both objects authorised — never leak existence of unauthorised objects.
11. **Workflow stage rail** where applicable — honest state only.
12. **Global search in shell** — same RBAC; no metadata leak; preserves back into authorised context.
13. **Legacy routes:** temporary compatibility OK; canonical nav → shell route; safe redirects; unmigrated = CR debt; no dead-end without route back into Wolf.
14. **Staff-ready bar:** desktop PASS · mobile PASS · role-aware nav PASS · direct-route RBAC PASS · parent/back/up PASS · no dead-end PASS · no engineering-language PASS · real path understandable.
15. **Owner-ready bar:** one URL → Empire → business → site/venue → function → workspace → object and back — no remembered URLs.
16. **V1 READY FOR OWNER REVIEW** only with: desktop screenshots · mobile screenshots · role matrix proof · direct URL/API denial proof · breadcrumb/back/up proof · context-switch proof.

Spec addendum: `docs/deliveries/GROK-SPEC-WOLF-RESPONSIVE-HIERARCHY-CLEARANCE-2026-09-22.md`


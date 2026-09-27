# GROK SPEC — WOLF GLOBAL SHELL
**Date:** 2026-09-22 ~15:50 WITA  
**Status:** TARGET SPEC · aligns with `#wolfnav` / sidenav.js one-chrome law  
## Constraints
- One `#wolfnav` / `sidenav.js` chrome owner — never second Boards menu.
- Extract/refactor tokens from existing `style.css` + sidenav CSS; do not restyle every page independently.
- Box-bound; Mac live not verified. ACTIVE factory packs not killed.
- Prod `:8787` sacred.

Permissions: `GROK-SPEC-WOLF-PERMISSIONS-AUDIENCE-2026-09-22.md` + RULE Permissions.

## Law
1. **Single chrome owner:** `sidenav.js` (or successor module that **replaces** it in-place — not a parallel nav).  
2. Manifest / IA config drives primary items — pages do not paste custom Boards lists.  
3. **SHELL shows what you may navigate · API enforces what you may access · DOMAIN enforces what you may do** — all three agree.  
4. Hidden menu ≠ permission.

## Shell regions (desktop)

```
┌─ #wolfnav (global nav) ─┬─ top context bar ─────────────────────────────┐
│ HOME                    │ [Org context switcher]  Breadcrumbs   Search   │
│ BUSINESSES              │ Title · Page-type · Live/Empty badge           │
│  GGV / AMG / BZG        │ [Needs You pill]              [Identity menu]  │
│ INTELLIGENCE            ├─ optional subnav (business grammar / tabs) ───┤
│ SYSTEM (if allowed)     │                                                 │
│ ─ On this page ─        │ main content                                    │
│ (section discover)      │                                                 │
└─────────────────────────┴─────────────────────────────────────────────────┘
```

### Global nav (`#wolfnav`)
- Sections match Target IA: HOME / BUSINESSES / INTELLIGENCE / SYSTEM.  
- **Retire** flat heading "Dashboards" as the only structure (keep discovery for On-this-page).  
- Filter by whoami grants + assignment scopes (scoped users: only allowed hrefs).  
- Stale dots / badges remain (control, not decoration).

### Org context
- Shows GROUP › ENTITY › SITE › BU/VENUE (and brand chip if relevant).  
- Multi-assignment: switcher lists **only** authorised scopes.  
- Brand never replaces entity/site/BU.

### Breadcrumbs
- Always map to hierarchy + page title.  
- Each crumb is a real parent route (or disabled honest stub).  
- DETAIL pages: `… › Workspace › Object`.

### Title + page-type
- H1 = human job name ("Uma Blu — Today").  
- Badge: page-type + live/empty/stub (no fake PROVEN).

### Subnav
- DASHBOARD: optional section pills.  
- WORKSPACE / MANAGEMENT: **business grammar** — Overview · Operations · People · Customers · Finance · Standards · Issues · Intelligence (omit ungated).  
- SYSTEM: Progress · Integrations · Sale · Factory.

### Search
- Global search entry in top bar.  
- **RBAC:** no title/snippet/existence/counts/metadata leak across unauthorised scopes (Permissions §10).

### Needs You
- Persistent pill/count from assignment-scoped queue.  
- Click → HOME Needs You or inline drawer — same scope rules.

### Identity
- Email / role label / sign-out (CF Access logout pattern already in sidenav).  
- Show active assignment; link to switcher if multi.

### Back / drill
- Explicit **Back to parent** control (not only browser back).  
- Drill-down preserves org context query/header.

### Phone nav
- ≤860px: nav closed by default; `#wolfnav-t` toggle (existing sidenav behavior — preserve).  
- Safe-area padding (Spartacus lesson).  
- Primary actions thumb-reachable; grammar as horizontal scroll tabs under title.

## Client / Buyer / Export modes
- Separate shells or shell flags: strip SYSTEM, internal Boards, Needs You internals.  
- Permissioned independently from view (Permissions §§4,12).

## Implementation note (Cursor pack 1)
- Refactor `sidenav.js` + shared `wolf-shell.css` tokens — **do not** fork a second nav.  
- Pages include one script + `data-wolf-*` attrs.  
- Keep working routes during migration (aliases stay).

# GROK SPEC — WOLF PERMISSIONS & AUDIENCE-AWARE SHELL
**Date:** 2026-09-22 ~15:50 WITA  
**Status:** STANDING TARGET · Owner follow-up NON-NEGOTIABLE  
**Cross-refs:** Role-Nav Matrix · Global Shell · Target IA · Page Types · RULE `docs/RULE-Wolf-Global-Navigation-Design-System-2026-09-22.md`

## Evidence / constraints
- Box-bound; live Mac catalog not opened this run. Spec is normative for factory gates.  
- Existing patterns: `sidenav.js` access_key/whoami (chrome only); `access-config.json` allow lists (prod sibling); Devi claim `API_AUTH_GATE=PENDING_CURSOR`.  
- Nav is **never** the sole security boundary.  
- ACTIVE factory packs not killed.

---

## 1. Identity → Role → Assignment → Scope → Audience-aware shell

| Layer | Meaning |
|-------|---------|
| **Identity** | Authenticated person (CF Access email / AUTH-*) |
| **Role** | Capability template (ROLE-BZG-HFB, finance, content, …) — not a person name in code |
| **Assignment** | Role bound to person for a time (ASG-*) |
| **Scope** | Org slice the assignment may touch |
| **Audience** | Projection class for shell (OWNER, CLIENT, …) |
| **Permission** | Concrete CAN SEE / CAN ACT / … codes |

**Hidden menu ≠ permission.** Removing a sidenav link never authorises or denials API access.  
**API auth is canonical.** UI filters are UX. Domain rules authorise mutations.

Global agreement:
> **SHELL** shows what you may navigate · **API** enforces what you may access · **DOMAIN** enforces what you may do — **all three agree.**

---

## 2. Four control layers (per surface / object)

| Layer | Question | Example |
|-------|----------|---------|
| **CAN SEE** | May this identity open the surface / list row? | Devi sees Uma Today |
| **CAN ACT** | May they mutate / submit / approve? | Devi cannot payment-approve |
| **CAN SEE DETAIL** | May they open drill fields beyond summary? | Labour $ total vs named wage lines |
| **CAN SEE ACROSS SCOPE** | May they aggregate or peer into sibling scopes? | Uma ops ⊄ other BZG venues; Habitat ⊄ Selo |

These are **separate grants**. Summary dashboards must not imply detail or cross-scope.

---

## 3. Audience classes

| Audience | Typical shell | Notes |
|----------|---------------|-------|
| **OWNER** | Full IA incl. SYSTEM | Widest legitimate projection **still via canonical perms** — no UI bypass |
| **EXECUTIVE / BUSINESS LEADERSHIP** | HOME + BUSINESSES (assigned) + limited INTEL | Cross-BU only if scope says so |
| **MANAGER** | BU/Venue Overview + grammar | People/Finance per grants |
| **OPERATOR / STAFF** | Today / Ops workspace | Narrow Needs You |
| **SPECIALIST** | Tool landing (content, legal, finance desk) | Not whole empire |
| **CLIENT** | Controlled projection only | Never inherit internal GGV nav |
| **SHAREHOLDER / INVESTOR** | Packaged views | Separate from operator |
| **BUYER / DUE DILIGENCE** | DD room | Export/Buyer Mode separately permissioned |
| **SYSTEM / ADMIN** | SYSTEM section | Factory, integrations |

**Person→Role→Assignment→Scope→Permission** — **no hard-coded people in page logic** (fixtures in tests/docs only).

---

## 4. Client-facing rules
Controlled projections only:
- **Never** inherit internal GGV (or any operator) nav.  
- **Never** leak: margin, staff chat, other clients, intel, admin, CR debt, audit internals, unrelated CRM, Owner notes — unless **explicitly** authorised.  
- Client Mode shell flag strips SYSTEM, Factory, Needs You internals, cross-client search.

---

## 5. Owner projection
Owner may see the widest legitimate set, but:
- Still checked through catalog/API permission codes.  
- No “if email == mrwolf skip auth” in new code.  
- UI may shortcut navigation; API must still verify.

---

## 6. Role-based landings (fixtures)

| Fixture | Landing |
|---------|---------|
| Matt / Owner | Empire Pulse |
| Devi | BZG F&B → Uma **Today** |
| Haikal | Content workspace (assigned brands) |
| Amanda | GGV management / Lead Spine |
| Client | Client project projection |
| Hotel / venue ops | Venue **Today** |

Multi-assignment → **authorised context switcher only** (no silent union of scopes).

---

## 7. Scope grammar
Scopes nest: `group / entity / site / venue-BU / brand-client-project / dept / object`.

**Examples (must fail closed):**
- BZG F&B ⊄ AMG  
- GGV employee ⊄ all clients  
- Habitat client ⊄ Selo  
- Uma ops ⊄ corporate BZG governance  
- Devi SCOPE-BZG-UMA ⊄ SCOPE-BZG-ENTITY (entity scope ended)

---

## 8. Summary vs detail drill-down

| Domain | Summary (CAN SEE) | Detail (needs CAN SEE DETAIL) |
|--------|-------------------|-------------------------------|
| Payroll | Headcount, total labour cost band | Named wages, bank accounts, tax IDs |
| Labour | Hours total, OT flag count | Per-person timesheet lines |
| Campaign spend | Brand spend total vs budget | Line-item vendor invoices, creative costs |
| Sales | Pipeline $ by stage | Individual deal notes, personal contacts |

DASHBOARD tiles use summary; DETAIL routes check detail grant. Cross-scope rollups need **CAN SEE ACROSS SCOPE**.

---

## 9. Sensitive classes (default deny detail / export)
payroll · compensation · bank/payment · staff PII · customer PII · legal · contracts · shareholder · security/audit · secrets · buyer DD

Surfaces touching these require explicit permission codes + audit log on ACT/EXPORT.

---

## 10. Search RBAC
Search must not leak across unauthorised scopes:
- No title, snippet, existence, counts, or metadata for denied objects.  
- Same for autocomplete and “recent”.  
- Unauth / no grant → empty result, not 403 enumeration of names (prefer empty + generic).

---

## 11. Intelligence inherits requester perms
- AKR / Decision Memory / wolf intelligence **not** a side door.  
- Retrieval allowlists filter by requester Assignment.Scope.  
- Provenance preserves scope; citations must not reveal out-of-scope docs.

---

## 12. Export / Client / Buyer Mode
Separate permissions from view:
- `CAN EXPORT` ≠ `CAN SEE`  
- Client Mode / Buyer Mode flags change shell **and** require mode permission  
- DD packs assembled only with Buyer DD grants

---

## 13. Test matrix (nav AND direct API/URL)

| Actor | Nav visibility | Direct URL to Progress | Direct API `/api/progress` | Direct Uma Today API | Notes |
|-------|----------------|------------------------|----------------------------|----------------------|-------|
| **Matt** | Full HOME/BUSINESSES/INTEL/SYSTEM | 200 (if exists) | allow | allow | Owner perms |
| **Devi** | BZG/Uma + Needs You; no SYSTEM | **fail** (403/deny) | **fail** | allow if commissioned | Manual URL must fail |
| **Haikal** | Content brands assigned | fail | fail | fail (unless scoped) | |
| **Client fixture** | Client shell only | fail | fail | fail | No GGV nav |
| **Unauth** | CF Access challenge / deny | fail | fail | fail | |

Prove both **chrome hide** and **server deny**. Hidden link is insufficient.

---

## 14. Global rule (repeat)
**SHELL** shows what you may navigate · **API** enforces what you may access · **DOMAIN** enforces what you may do — **all three agree.**

Factory register gate: new dashboard surfaces must declare audience + required permission codes; unmigrated = design-system **and** permissions debt.

# RULE — Authorised Knowledge Resolution

**LOCKED 2026-09-17 (Matthew).** Architectural requirement. Backlog for future software — **not** permission to build now.

## Provenance

Habitat Brand Intelligence first pass (local Beta only) mis-labelled several areas ABSENT/PARTIAL. Full authorised sweep the same day found client brand guidelines, voice, audience, visual identity, products/offers, pillars, NAS/Drive/vault material, and resolved Manrope vs Inter **without** asking a human. That failure → correction is the proof case.

Related: `docs/deliveries/HABITAT-FULL-AUTHORISED-KNOWLEDGE-SWEEP-2026-09-17.md` · backlog `docs/backlog/AUTHORISED-KNOWLEDGE-RESOLVER-2026-09-17.md`

## Principle

**EMPTY FIELD ≠ UNKNOWN.**  
An empty canonical Wolf field/store is **not** proof that information is unknown.

**UNKNOWN REQUIRES SEARCH EVIDENCE.**

Before asking a human for **material** information, Wolf Intelligence should (where appropriate and authorised):

1. ENTITY / BRAND / OBJECT SCOPE  
2. CHECK CANONICAL TRUTH  
3. DISCOVER RELEVANT AUTHORISED SOURCES  
4. RETRIEVE  
5. RECONCILE IDENTITY  
6. CLASSIFY SOURCE AUTHORITY  
7. CHECK FRESHNESS  
8. DETECT CONFLICTS  
9. RETURN ANSWER WITH PROVENANCE / CONFIDENCE  
10. ASK HUMAN ONLY FOR MATERIAL UNRESOLVED TRUTH  

## Terminology (do not flatten)

| Term | Meaning |
|---|---|
| **NOT CANONICAL** | Information may exist elsewhere; not promoted into canonical Wolf truth |
| **NOT FOUND** | Reasonable authorised retrieval completed; nothing relevant found |
| **INACCESSIBLE** | Potentially relevant source exists; Wolf cannot inspect it now |
| **CONFLICTED** | Multiple relevant sources disagree; authority/freshness does not safely resolve |
| **UNKNOWN** | No trustworthy answer after relevant authorised retrieval/reconciliation |

Also preserve:

- **SOURCE FOUND ≠ SOURCE AUTHORITATIVE ≠ FACT CANONICAL**
- **AI INFERENCE ≠ SOURCE EVIDENCE**

## Human interruption

**DO NOT ASK A HUMAN FOR INFORMATION WOLF CAN REASONABLY RETRIEVE FROM AN AUTHORISED SOURCE.**

## Anti-crawl

Future implementation **must** use deterministic source selection, scope, cost, and timeout rules. A simple question must not trigger an uncontrolled crawl of every connected system.

## Software-first

This is a **software orchestration / skill** gap — not a default new-agent hire (`RULE-Software-First-Agent-Scarcity`).

## Explicit non-actions (until Matt opens a slice)

- Do **not** build the resolver yet  
- Do **not** promote Habitat knowledge into `memory_items` yet  
- Do **not** ask humans remaining Habitat unresolved truths unless a **live workflow** needs the answer  

## Habitat remaining unresolved (preserve; do not nag)

- Live inventory / current pricing  
- Scarcity / ROI unlock policy  
- Face / model / footage rights  
- Keen Eye contractual detail  
- Conflicting uppercase vs lowercase headline operational rules  
- Inaccessible Canva pixel truth  


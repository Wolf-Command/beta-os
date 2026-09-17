# BACKLOG — Authorised Knowledge Resolver (software)

**Status:** BUILD OPENED 2026-09-18 — overnight P3 (bounded Beta slice)  
**Locked:** 2026-09-17  
**Build opened:** Matt CONTINUE overnight 2026-09-18  
**Canon:** `docs/RULE-Authorised-Knowledge-Resolution-2026-09-17.md`  
**Proof case:** Habitat full authorised knowledge sweep 2026-09-17  

## Problem

Empty canonical fields were treated as UNKNOWN/ABSENT. Authorised knowledge already existed (NAS brand guide, Obsidian vault, Drive, wolf-system packs). Humans were about to be asked questions Wolf could answer.

## Desired future behaviour

Entity/Brand/Object-scoped resolve pipeline:

SCOPE → CANONICAL → DISCOVER → RETRIEVE → RECONCILE → AUTHORITY → FRESHNESS → CONFLICTS → PROVENANCE ANSWER → HUMAN ONLY IF UNRESOLVED

With deterministic source allowlists, cost/timeout caps (no infinite crawl).

## Non-goals (until separate Matt slice)

- Vector DB / new search product  
- New agent  
- Auto-promote into canonical memory  
- Habitat memory_items promotion  
- Asking staff for backlog “nice to know” gaps  

## Suggested future owner

Peaches governs · Grok designs · Cursor implements **when** Matt opens a bounded Beta slice.

## Acceptance sketch (when built)

- Empty field + found authorised source → NOT CANONICAL (or answer with provenance), never silent UNKNOWN  
- Inaccessible source labelled INACCESSIBLE  
- Conflicts returned CONFLICTED with both sides  
- Timeout/cost caps proven  
- Habitat Manrope-vs-Inter class of conflict auto-scoped (brand vs UI) without human  


# GROK PLAN — Wolf NAS Library + Upload P0 — 2026-09-22

**Run id:** `BF-wolf-nas-library-upload-p0-20260922`
**Owner:** Connection Commissioning package APPROVED (recommended READ/WRITE; ClickUp/Telegram RETIRED)
**Bound:** Beta `:8788` only. Production `:8787` sacred — no mutate.
**Head note:** shared dirty `serve_beta` OK to extend surgically; defer commit if needed.

## Goal
Connect existing Content Engine / Smart Upload / Library to real NAS canonical storage.
Wolf = staff interface. NAS = canonical media. B2 = backup/DR (observe only this slice).
Do NOT invent a second upload product. Do NOT destroy/rename/move/bulk-delete NAS assets.

## Current gap (evidence)
- `/Volumes/01-Media-Library` mounted; `nas_status.connected=true`
- Smart Upload writes `library_v2` only; `nas_received=false`
- content_library.sqlite assets~9; NAS shallow ~40k files unindexed

## In scope
1. NAS source registry module (roots, read-only inventory API) — preserve original path/provenance
2. Safe index: hash + metadata into Beta catalog WITHOUT mutating NAS files
3. Upload pipeline: staging -> validate -> hash -> dup check (never silent discard) -> required metadata only -> scope/permission check -> deterministic canonical NAS placement under Media Library -> asset index -> search; preserve original filename; nas_received=true only when file really on NAS
4. Library UI in Global Wolf shell: search/filters/thumbnails/preview/detail/provenance/upload/Smart Upload/select all/deselect/bulk+ZIP download — desktop+mobile responsive
5. RBAC: Person->Role->Assignment->Scope->Permission->Audience; four layers; URL/API/search deny wrong scope; no path leakage
6. Integration Health: classify ClickUp + Telegram as RETIRED / HISTORICAL ONLY (not waiting to commission)
7. Tests: unit + live Beta prove bars short of Haikal human (mark test assets; audited cleanup)

## Out of scope
- Full tree hash of all 40k+ in one night if too slow — start Brand-Assets + _Imports sample + upload path; background index job OK
- B2 restore drill / kicking full B2 sync
- Production deploy
- Inventing CAP READY / staff-commissioned flag
- Klaviyo/Metricool write, Email auto-send, ESB/Yanolja write
- Destroying NAS or rewriting historical metadata

## Success / EXIT
- Suite PASS with FAIL=0
- Live `:8788`: authorised upload lands on NAS path; nas_received true with evidence; search finds it; wrong-scope 403
- whoami honesty: proven=false ready=false; staff_ready=false
- Docs: GROK-REVIEW + claim; update Connection Register NAS section
- `:8787` untouched

## Cursor rules
- ASCII prompts only (no special inequality glyphs)
- Prefer durable Shell-tracked launch
- Read RULE-Wolf-Connection-Commissioning-NAS-GoLive-2026-09-22.md
- Preserve Haikal-liked UX; fix architecture underneath

EXIT: SUCCESS when tests + review evidence written.

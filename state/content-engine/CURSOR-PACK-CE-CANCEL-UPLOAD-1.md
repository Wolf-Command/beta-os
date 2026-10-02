# CURSOR PACK — CE-CANCEL-UPLOAD-1 (Beta only)

Workspace: `/Users/wolfterminal/beta-os`  
Branch: `build/wolf-command-rebuild` (local only — no origin/push)  
Prod `:8787`: READ-ONLY. Never mutate prod.

## Goal
Implement Owner-approved Cancel Upload + post-upload metadata correction for Content Engine Smart Upload, preserving Haikal’s feedback as origin.

## Read first
- Existing smart_upload / content library / NAS store paths
- Current batch progress UI
- Prior Haikal 14fail repair notes under `state/` if present
- Do not invent NAS delete for late Cancel

## Implement
1. Batch Cancel Upload + per-file cancel where practical
2. Lifecycle statuses: CANCELLED before/during transfer; after commit → stop processing + clear “already uploaded” message (no fake cancel)
3. Temp partial cleanup on abort
4. Batch progress: overall, current, completed, remaining, failed, cancelled + Cancel Upload
5. One confirm for Cancel Remaining
6. Metadata correction (brand/stage/content type/subject/location/details) with audit trail; no re-upload
7. Tests covering Owner ENGINEERING PROOF list (incl. multi-file MOV)
8. Update Haikal retest brief to include cancel + stage-correct steps
9. Stamp RESULT under `state/final-completion/.../CE-CANCEL-UPLOAD-1-RESULT.*`
10. Commit local slice only; leave staff_ready=false

## Exit
EXIT:0 only when tests green and RESULT stamped. Report paths + commit SHA.

# Wolf NAS Source Registry — 2026-09-22
Honesty: folder names are EVIDENCE not automatic facts. Unknown = UNKNOWN.

## Mounts (SMB 192.168.77.130 Mr Wolf)
| Volume | Role (working) | Notes |
|--------|----------------|-------|
| /Volumes/01-Media-Library | Canonical operational media | TARGET for Wolf Library |
| /Volumes/00-Editing-Workspace | Editing scratch | Not primary library |
| /Volumes/02-Stock-Assets | Stock | Separate |
| /Volumes/03-Templates | Templates | canva/capcut/etc |
| /Volumes/04-Time-Machine | Time Machine | Not library |
| /Volumes/05-Wolf-Vault-Mirror | Vault mirror | Backup-ish; not ops library |

## 01-Media-Library top (evidence)
AMG, AMG-Atrium, BZG, Brand-Assets, Clients, GGV, _Imports, _Shared, _clickup-attachment-archive (HISTORICAL), _needs_sorting
Shallow maxdepth4 file count ~39986 (not full tree).

## Indexing state
P0 sample index: Brand-Assets (+ _Imports evidence) capped sample hashed into `state/nas-index/` + Beta `nas_index` table (READ-only; NAS files not mutated).
Index-continue (2026-09-22 v2): additional safe tops sampled with per-folder caps — AMG, AMG-Atrium, BZG, GGV, Clients, _Shared (AMG may be empty). Full ~40k tree still NOT indexed — do not claim complete.
Upload path: Smart Upload → Beta `library_v2` mirror → canonical `_Imports/Wolf-Library/{brand}/{stage}/{YYYY}/` (test lane under `_test/`).
`nas_received=true` only after verify on NAS.
Search: `/api/nas/index/search?q=&folder=` scope-gated; relative paths only; no `/Volumes/` leak.
Honesty: proven=false ready=false staff_ready=false. Haikal human upload/search/preview/download still required before staff go-live.

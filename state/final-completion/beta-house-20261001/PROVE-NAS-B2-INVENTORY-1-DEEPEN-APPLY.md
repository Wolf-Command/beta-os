# PROVE-NAS-B2-INVENTORY-1-DEEPEN

as_of: 2026-10-01T07:59:52+08:00 · Prod :8787 UNTOUCHED (pid 15975) · restore **NOT_RUN**

## NAS (timed)
| Mount | Status | Top entries | Files (maxdepth) | ms |
|---|---|---:|---:|---:|
| 01-Media-Library | OK mount | 13 | 38091 @d3 | ~20s |
| 00-Editing-Workspace-3 | OK mount | 9 | 843 @d3 | ~1s |
| 02-Stock-Assets-1 | OK mount | 8 | 207 @d3 | ~0.5s |
| 03-Templates | OK mount | 7 | 1 @d2 | 34ms |
| 05-Wolf-Vault-Mirror | OK mount | 5 | 21 @d2 | 170ms |
| 00-Editing-Workspace[-1/-2] | **PERMISSION_DENIED** | — | — | — |
| 02-Stock-Assets (bare) | **PERMISSION_DENIED** | — | — | — |

Brand top on 01-Media-Library: AMG / BZG / GGV / _Imports present.

Beta `/api/nas/status`: connected=true, path=01-Media-Library, nas_received=false, staff_ready=false, proven=false.

## B2 (rclone dry-read)
- Remotes: b2nas / wolfb2 buckets list OK.
- Freshness (lsjson ModTime): media `.cache` newest **2026-09-30T23:56:58Z** (~07:56 WITA 2026-10-01).
- `rclone about` unsupported on B2 root (honest).
- **Restore: NOT_RUN** (no Owner-approved drill this run).

## Honesty
No writes, no restore, no invented full-tree index claim. full_tree_indexed=false.

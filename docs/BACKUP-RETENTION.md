# Beta catalog backup retention (Owner P0, 5 Oct 2026 20:42 WITA)

## Incident (5 Oct 2026)
Studio free space fell to ~13 GB (97–98 % used). Two Beta test-time writers, both copying the
~114 MB live catalog `catalog/content_library.sqlite` on every run and never cleaning up:

1. **`state/build-factory/tmp-f1/wolf-f1-*/content_library.sqlite` — 53 GB (510 dirs).**
   `scripts/core/canonical_guard.py::backup_catalog()` gives each test process an isolated
   consistent copy of the catalog. Nothing removed it. Factory slices run dozens of test
   processes per slice (observed ~1 copy every 2 s at 20:50 WITA).
2. **`catalog/backups/pre-*.sqlite` — 74 GB (31,858 entries; +27.6 GB on 5 Oct).**
   Every migration in `scripts/migrations/` did `shutil.copy2(db, catalog/backups/pre-...)`
   unconditionally — also when a regression test ran the migration on a throwaway COPY, and
   when the migration was an idempotent no-op. e.g. `test_bzg_p2p_harden1_20261005.py` re-runs
   7 P2P migrations → 7 × 109 MB per test run. Tests also `mkdtemp(dir=catalog/backups)`
   (`fcr-*`, `bzg-close-*`, `intel-connect-dm-*`) and never clean those dirs.

## Fixes in code
| Where | Change |
|---|---|
| `scripts/core/canonical_guard.py` | test catalog copy is removed at process exit (`atexit`); refuses a new copy if Studio free space would drop below **8 GB** (`WOLF_TMPF1_MIN_FREE_GB`) and posts `STUCK` to `state/build-factory/NOTIFY-QUEUE.jsonl`. `WOLF_KEEP_TMPF1=1` keeps the copy for debugging. |
| `scripts/core/backup_policy.py` + 39 migrations | `premig_backup()` replaces `shutil.copy2`. Test/scratch DB → no copy in `catalog/backups` (APFS clone next to the scratch DB). Live DB → **dedupe** (skip if sha256 equals the last backup of that DB), **free-space guard** (refuse if Studio would drop below **50 GB**, `WOLF_BACKUP_MIN_FREE_GB`; emits `FAIL_NO_SELF_REPAIR` to NOTIFY-QUEUE). Events: `state/reliability/BACKUP-POLICY-EVENTS.jsonl`. |
| `scripts/ops/catalog_backup_retention.py` | archive → verify → prune (below). |

Not yet patched (left for the owning slice, it was mid-edit): `migrate_bzg_p2p_payment_record1_20261005.py`
still uses a raw `shutil.copy2` — switch it to `premig_backup` when that slice finishes.

## Local retention (Studio)
* Kept locally: the **newest known-good** live-catalog backup (PRAGMA integrity_check = ok,
  ≥ 50 tables), plus the newest known-good per day for the **last 2 days**, plus anything
  younger than **60 min** (may still be in use by a running test).
* Everything older is archived to the NAS and the Studio copy deleted **only after** verification.

## NAS archive
`/Volumes/05-Wolf-Vault-Mirror/WolfArchive/beta-os/catalog-backups/<RUN-DATE>/`
(deliberately outside `.../mac-studio/`, which `r2-sync.py` mirrors to cloud.)
* `objects/<aa>/<sha256>.zst` — one zstd object per unique file ≥ 1 MB (identical backups stored once).
* `bundles/small-<birth-day>.tar.zst` — files < 1 MB grouped by entry birth day.
* `MANIFEST-<stamp>.json|csv` — one row per source file: source path, dest path, size, sha256 src,
  sha256 dest, readable, verified_at, studio_copy_deleted_at. Copy in `state/reliability/`.
* Verification per file: local sha256 == sha256 of bytes read BACK from the NAS with the macOS page
  cache bypassed (F_NOCACHE), size equal; SQLite `PRAGMA quick_check` = ok on the byte-identical
  source; bundles re-listed and every member hashed on readback.
* Restore: see `RESTORE.md` in each run folder (`zstd -d`, `tar -x`).

### NAS retention policy (report-only until approved)
Daily for 14 days, then one per ISO week for 8 weeks, then drop. Pruning on the NAS is **not**
automated yet — no NAS deletion without an explicit owner OK.

## Schedule
LaunchAgent `net.wolfcommand.catalog-backup-retention` runs
`catalog_backup_retention.py --delete --limit-gb 20` every 6 h. If the NAS is not mounted it posts
`STUCK` (`nas_not_mounted`) to NOTIFY-QUEUE and deletes nothing.

## Never deleted by this policy
Live DBs (`catalog/*.sqlite`), Beta data, evidence, uploads, git trees, deployment, secrets/config,
the newest known-good backup, `~/WolfRecoveryPoints/*`, anything of Production
(`~/.openclaw/workspace/wolf-system`, pid 1297). Backups stay out of git (`catalog/` is gitignored).

## Hard disk guards (factory)
`scripts/build-factory/bf_disk_guard.py`, called at the start of every `bf_supervisor.tick`:

| Free space | Level | Action |
|---|---|---|
| < 100 GB | WARN | NOTIFY `WARNING` (`studio_free_below_100gb`); work continues |
| < 50 GB | CLEAN_PAUSE | NOTIFY `STUCK`; **no new dispatches**; auto-delete disposable `tmp-f1` wolf-f1-* dirs older than 5 min |
| < 25 GB | P0_PROTECTION | NOTIFY `FAIL_NO_SELF_REPAIR`; refuse all disk-growing nonessential jobs |

Env overrides: `WOLF_DISK_WARN_GB`, `WOLF_DISK_CLEAN_GB`, `WOLF_DISK_P0_GB`.
Events go to `state/build-factory/NOTIFY-QUEUE.jsonl`.

# B2 restore drill — 29 Aug 2026

**Timestamp:** 2026-08-29 09:16 WITA (Asia/Makassar, UTC+8)

**Verdict:** B2 updating yes, R2 quiet yes, restorable yes. Restored 337965245 bytes; sha256 7885fae76e260c6a6e7235c994178edf2724988a528fe07712213c8963b18ca6 match yes. Synology B2 2805440683918 bytes (2.552 TiB, 118343 objects). Footage B2 2915674453293 bytes (2.652 TiB, 197096 objects). Daily-backups prefix 18994503650 bytes (17.690 GiB, 128 objects). Cap-monitor floor 5322.27 GB at 07:07 WITA (wolf-cold-archive size timed out).

## Architecture (locked 18 Aug 2026)

- Only B2 gets updates. R2 writes stay OFF for cost.
- Real restorable offsite = B2 + Synology NAS. Time Machine is the Mac copy.
- R2 is not primary. R2 objects were left alone.
- No deletes recommended on B2, R2, or NAS.

## Mac-side last successful B2 writes

| Job | Last write (WITA) | Evidence |
|---|---|---|
| `com.wolfcommand.backup` / backup.py | 2026-08-29 02:00:04 run; B2 object mtime 2026-08-29 02:00:27 | `backup_status.json`: last_run 2026-08-29T02:00:04, local_ok true, b2_ok true, local_size_bytes 337965245, files_count 13341. Log: pushed 2 files to `b2:wolf-cold-archive/daily-backups`. Object `wolf-backup-20260829.tar.gz` listed on B2 at 337965245 bytes. |
| `com.wolfcommand.footage-b2-sync` | 2026-08-29 02:08:04 start → 08:07:17 end, rc=0 | `~/.openclaw/logs/footage-sync.log`: Transferred 13.733 GiB / 13.733 GiB, 1653/1653 files, 195464 checks. Dest `wolfb2crypt:` → `wolf-footage-archive`. This is Mac rclone of `/Volumes/01-Media-Library`, **not** Synology Cloud Sync. |
| `com.wolfcommandsystem.b2-archive` | 2026-08-23 08:06:02 (Sunday weekly) | `b2-archive-state.json`: last_success 2026-08-23T08:06:02+08:00, last_file_count 149947, last_bytes 22857570813, dest `b2:wolf-cold-archive/wolf-vault-mirror/mac-studio/`, ok true. Next Sunday slot is 30 Aug. |
| `com.wolfcommand.b2-archive-proof` | 2026-08-29 09:00:02 (read-only check) | Proof OK: last_success 2026-08-23 08:06:02 (6.0d ago), files 149947. Expected for a Sunday job. |
| `com.wolfcommand.b2-cap-monitor` | 2026-08-29 07:07:18 (read-only size) | `b2-usage.json`: used_gb 5322.27 floor, buckets_counted footage + wolf-media-nas, `b2:wolf-cold-archive` TimeoutExpired. write_blocked false. |
| `com.wolfcommandsystem.daily-backup` | 2026-08-29 03:17:27 | **Local only** (`~/.openclaw/backups/wolf-system/2026-08-29`). Not a B2 write. Loaded, last exit 0. |

`/tmp/nas-backup-active.lock` was **not present**. Not cleared. `/tmp/footage-b2-sync.lock` also absent.

`restore-drill.py` was inspected and **not run**. Default path samples R2. Manual one-file B2 restore used instead.

## Synology → B2 evidence

DSM Cloud Sync UI/logs were **not reachable** from the Mac (no `@CloudSync` status/log on mounted shares). Evidence is rclone only.

- Remote `b2nas:` → bucket `wolf-media-nas` (Synology Cloud Sync path; separate from Mac footage-b2-sync).
- `rclone size --fast-list b2nas:wolf-media-nas`: **118343 objects, 2805440683918 bytes (2.552 TiB)**. Elapsed 66.4 s.
- Prefixes match `/Volumes/01-Media-Library`: AMG, AMG-Atrium, BZG, Brand-Assets, Clients, GGV, _Imports, _Shared, _clickup-attachment-archive, _needs_sorting, plus `.cache`.
- Recent object mtimes: cache/thumbnails dated **2026-08-28** (latest seen 15:34 WITA). Non-cache content in last 7d at depth 4: `_Shared/Training-Centre/files/f59e137ced1f.mp4` **25428404 bytes**, mtime **2026-08-26 21:10:51**; sibling mp4 4510270 bytes same day.
- 18 Aug cap-monitor “~431 GB” for this bucket is **stale**. Live size is 2.552 TiB.

## Restore drill (the proof)

- **Remote:** `b2:wolf-cold-archive/daily-backups/wolf-backup-20260829.tar.gz`
- **Method:** `rclone copyto` into new temp dir `/tmp/wolf-b2-restore-drill-20260829` (not production).
- **Bytes transferred:** 337965245 (must be > 0; was). Restore wall time 47.7 s.
- **sha256 restored:** `7885fae76e260c6a6e7235c994178edf2724988a528fe07712213c8963b18ca6`
- **sha256 local original:** `7885fae76e260c6a6e7235c994178edf2724988a528fe07712213c8963b18ca6` (`~/.openclaw/backups/daily/wolf-backup-20260829.tar.gz`, same byte count)
- **Match:** yes → restorable yes
- After hashing, **only** the Mac temp dir was deleted. Nothing deleted on B2 / R2 / NAS.

Secrets gpg names exist beside the daily tarball (`wolf-secrets-YYYYMMDD.tar.gz.gpg`). Not restored. No contents.

## Bucket sizes (rclone, live)

| Target | Result |
|---|---|
| `b2nas:wolf-media-nas` | 118343 objects, 2805440683918 bytes (2.552 TiB) — 66.4 s |
| `wolfb2:wolf-footage-archive` | 197096 objects, 2915674453293 bytes (2.652 TiB) — 101.3 s |
| `b2:wolf-cold-archive/daily-backups` | 128 objects, 18994503650 bytes (17.690 GiB) — 3.3 s |
| `b2:wolf-cold-archive/wolf-command` | 16 objects, 89490 bytes (87.393 KiB) — 2.5 s |
| `b2:wolf-cold-archive` (full) | **TIMEOUT after 120 s** (same as cap-monitor). Prefixes present: `daily-backups`, `wolf-command`, `wolf-vault-mirror`. |
| `b2:wolf-cold-archive/wolf-vault-mirror` | **TIMEOUT after 90 s**. Last successful Mac sync 2026-08-23: 149947 files, 22857570813 bytes reported in state (last-run transfer, not a live total). |

Cap-monitor 2026-08-29 07:07:18 WITA: 5322.27 GB **floor** (~42.6% of 12500 GB cap), 1 of 3 buckets failed (`wolf-cold-archive` timeout). NoneGB is not the latest line. write_blocked false.

## Job map

| Name | Dest | Loaded | Last write |
|---|---|---|---|
| com.wolfcommand.backup | `b2:wolf-cold-archive/daily-backups` | yes (not running, last exit 0) | 2026-08-29 02:00 WITA |
| com.wolfcommandsystem.daily-backup | local `~/.openclaw/backups/wolf-system/YYYY-MM-DD` | yes (not running, last exit 0) | 2026-08-29 03:17 WITA (not B2) |
| com.wolfcommandsystem.b2-archive | `b2:wolf-cold-archive/wolf-vault-mirror/mac-studio/` | yes (not running, last exit 0) | 2026-08-23 08:06 WITA (Sunday) |
| com.wolfcommand.footage-b2-sync | `wolfb2crypt:` / `wolf-footage-archive` from `/Volumes/01-Media-Library` | yes (not running, last exit 0) | 2026-08-29 08:07 WITA, 13.733 GiB |
| com.wolfcommand.b2-cap-monitor | read-only size: `b2:wolf-cold-archive`, `wolfb2:wolf-footage-archive`, `b2nas:wolf-media-nas` | yes (not running, last exit 0) | 2026-08-29 07:07 WITA |
| com.wolfcommand.b2-archive-proof | read-only state check | yes (not running, last exit 0) | 2026-08-29 09:00 WITA |
| com.wolfcommand.secrets-offsite | secrets blob (names only; not drilled) | yes (not running, last exit 0) | not inspected (avoid secrets) |
| com.wolfcommandsystem.r2-sync | would be `r2:ggv-media` / `bzg-media` / `amg-media` | **not loaded**; plist `com.wolfcommandsystem.r2-sync.plist.disabled-r2-cost-20260818` | last state 2026-08-16 (stale; job off) |
| com.wolfcommandsystem.r2-sync-slow | same R2 buckets | **not loaded**; plist `com.wolfcommandsystem.r2-sync-slow.plist.disabled-r2-cost-20260818` | last_success_slow 2026-08-16 (stale; job off) |

rclone remotes present (names only): `b2:`, `wolfb2:`, `wolfb2crypt:`, `b2nas:`, `r2:`, `r2archive:`. No rclone process to `r2:` at map time or recheck. One leftover `rclone size b2:wolf-cold-archive` from this drill’s size attempt; not an R2 upload.

## Explicit

- No deletes recommended. Do not delete B2, R2, or NAS objects.
- R2 is not primary. R2 objects left alone. R2 writes remain off.
- launchd was mapped read-only. No kickstart. Lock file not cleared.
- No secrets, tokens, rclone config, or secrets-archive contents in this report.

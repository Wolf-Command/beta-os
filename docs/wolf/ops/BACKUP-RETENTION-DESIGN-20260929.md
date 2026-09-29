# Mac Studio backup + retention design — PROPOSAL (29 Sep 2026)
Status: DRAFT for Matt. Nothing below is applied. Old 03:16 `com.wolfcommandsystem.daily-backup` stays unloaded (plist kept, never re-enable).

## What exists today (verified 29 Sep)
| Layer | Job | What | Where | Versioned | Verified |
|---|---|---|---|---|---|
| A | com.wolfcommand.backup 02:00 | state/vault/personal/atrium/atlas-vault/nirmata data tarball (no media, no venv, no code) 401 MB, 7 kept | local + B2 wolf-cold-archive/daily-backups | yes, 7 days | 29 Sep: B2 download sha256 = local; extract 7,694 files; 12/12 sqlite integrity ok; 8/8 sample match live |
| A2 | same | secrets tarball gpg | local + B2 | yes | decrypts; 39/39 live secrets present (names only, never written) |
| B | same, step 4b | git push 5 repos | GitHub | yes | fresh clone of all 5: HEAD = local, fsck ok |
| C | wolf-vault-rsync 02:39 | full ~/.openclaw backups+workspace+credentials+secrets-vault mirror (includes media, uncommitted, atlas-control) | NAS 05-Wolf-Vault-Mirror (83% full) | NO (rsync --delete mirror) | log OK 29 Sep 02:50 |
| D | r2-sync | NAS/state to R2 | R2 | — | DISABLED since 18 Aug (cost) |
| X | daily-backup 03:16 | full copytree ~29-34 GB/day | local only | 7 | ROOT CAUSE of 29 Sep disk-full; unloaded |

## Gaps
1. Full workspace state (14 GB media, 11 GB atlas-control, 1,070 uncommitted prod files) exists only on Mac + NAS mirror. The mirror is not versioned: a bad delete or corruption copies over the NAS copy the next night. Same building, no off-site copy.
2. The 22 Sep full copy (33 GB) is the only versioned local point for that class. It ages with no replacement.
3. No scheduled restore drill. The last automated proof was this manual one.
4. The old job crashed on an unreadable file (state/hr-sop/HRD-PRF-001_SOP PENILAIAN KINERJA MINGGUAN.docx), and its prune only ran after success.

## Proposal (recommended)
1. **Versioning on NAS, not the Mac.** Turn on Synology snapshots for the 05-Wolf-Vault-Mirror share: 7 daily + 4 weekly. Costs 0 Mac disk and gives point-in-time copies of layer C. Matt or the NAS admin enables it in Synology Snapshot Replication (needs a Btrfs volume; check first).
2. **Small local rollback (optional, if 1 isn't possible).** A new job `wolf-snapshot.py` at 03:16 replaces the old one:
   - `rsync -a --link-dest=<previous>` into `~/.openclaw/backups/wolf-system-snap/YYYY-MM-DD.partial`, renamed to final only on success, with a manifest.
   - Excludes `.venv*`, `venv`, `node_modules`, `__pycache__`, `.git` (GitHub has it), `*-verify/`, `prompt-cache`, `craft-library`, `*.bak*`, `*.tmp`.
   - Unchanged files are hardlinks, so each extra day costs only what changed.
   - Keep 3. Prune runs FIRST and in a `finally`, and deletes any `.partial`, so a failed run can't leak space.
   - An unreadable file is logged and skipped, never an abort.
   - Pre-flight: skip the run if free space is under 50 GB. Post: alert if the snapshot is over 40 GB.
   - Delete the 22 Sep full copy only after the new job has 3 good snapshots and a restore test from one of them passes.
3. **Keep layers A and B unchanged.** The B2 tarball + GitHub is the durable off-site copy.
4. **Weekly restore drill (automated).** Every Monday: `restore-drill.py --tier tier1,secrets --sample 8`, plus a B2 download sha256 check, plus a fresh clone of the 5 repos into /tmp and cleanup. It reports only on a failure. Read-only against prod.
5. **Disk guard.** Pulse is live now: under 50 GB AMBER, under 20 GB RED wakes Peaches, and any new dated backup folder is flagged.
6. **Open decision (cost).** Off-site copy of full state (media + atlas-control). Today it is Mac + NAS only. Options: (a) accept, (b) re-enable R2 for the NAS mirror only, (c) B2 weekly encrypted tar of workspace/state minus rebuildables. Needs Matt; it costs money.

## Rollback
Everything is additive. The old plist is kept (unloaded). No changes to backup.py, B2, git or the NAS mirror.

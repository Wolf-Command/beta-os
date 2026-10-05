# Beta ⇄ GitHub lifecycle (Owner P0, 5 Oct 2026 20:30 WITA)

## What is served where

| Lane | Served tree | Process | Git ref | GitHub |
|---|---|---|---|---|
| **Beta** (beta.wolfcommand.net → 127.0.0.1:8788) | `/Users/wolfterminal/beta-os` (entrypoint `scripts/serve_beta.py`) | launchd `net.wolfcommand.serve-beta` (KeepAlive) | branch **`beta`** (factory snapshots) — local checkout stays on `build/wolf-command-rebuild` | `wolfcommand/beta-os` (private), branch `beta` |
| **Production** (127.0.0.1:8787, pid 1297) | `/Users/wolfterminal/.openclaw/workspace/wolf-system` | launchd `com.wolfcommandsystem.dashboards-serve` | `live/mac-studio-gates` @ `7c5564a` (+ uncommitted local changes) | `wolfcommand/wolf-system` |

* Beta is **this tree, reloaded by the factory** via `scripts/beta_restart.py` (gated by `bf_reload_gate.py`).
* Production is a **separate tree and repo**. Nothing is ever auto-deployed from `beta` to Production.
  Promotion to Production is a separate, owner-approved step.
* `beta-os` history before 5 Oct: `main` (`3c10fc2` baseline) → `build/wolf-command-rebuild` (last commit
  `0b0e50d`, 2 Oct). Everything Oct 2 → Oct 5 (Daily Close 6-step, iPhone photo, Petty Cash, BZG import,
  P2P, Finance, Zayen switcher) was uncommitted on the Mac until the October Beta baseline on `beta`.

## Slice lifecycle (mandatory order)

1. **BUILD** — Peaches / factory worker edits Beta code (single writer, `WRITER.lock`).
2. **LOCAL TEST** — slice regression tests, in-process (never restart Beta from a test).
3. **COMMIT + PUSH** — `python3 scripts/build-factory/bf_git_snapshot.py --reason "<SLICE-ID>"`
   creates a commit on `beta` from the live tree and pushes it to `wolfcommand/beta-os`.
   `scripts/beta_restart.py` runs this automatically **before** every kickstart, so a reviewable diff
   always exists before the code goes live. Result: `state/build-factory/GIT-SNAPSHOT-LAST.json`.
4. **DEPLOY / RELOAD** — `scripts/beta_restart.py --reason <SLICE-ID>` (gate may answer RELOAD_HELD).
5. **PUBLIC HEALTH CHECK** — beta.wolfcommand.net `/api/health` 200.
6. **RENDERED WORKFLOW TEST** — `bf_ready_gate.py` (rendered surfaces, stability).
7. **READY FOR HUMAN TEST**.

### Review policy
* **Peaches remains the builder.** **ChatGPT reviews versioned diffs** on GitHub
  (`https://github.com/wolfcommand/beta-os/commits/beta`, or compare `beta~1...beta`).
* **P0 changes — finance, money, security, auth/RBAC, data/migrations, deploy/reload/factory —** must be
  committed + pushed (snapshot `pushed: true`) **before** READY FOR HUMAN TEST. If the push failed,
  the slice is not HUMAN READY.
* **Trivial visual fixes** (copy, spacing, colour) still get snapshotted at reload but do not need to wait
  for a ChatGPT review before HUMAN READY.
* Significant Beta code is **never Mac-only**.

### Safety rules for the snapshot
* Private index + git plumbing: never touches HEAD, the worker's index, or the worktree; never resets,
  cleans, stashes, checks out, or force-pushes. Safe while a slice holds `WRITER.lock`.
* `.gitignore` excludes secrets (`.env*`, keys), runtime DBs (`*.sqlite*`), `catalog/` (incl. ~61 GB
  backups), `backups/`, uploads, raw bank statements, receipt / petty-cash / nota photos, PDFs/XLS/CSV
  under `state/`, logs, caches, tarballs.
* Refuses (exit 5) if any changed blob matches a credential pattern or exceeds 20 MB.
* Workers still must **not** run git commit/push/reset/checkout/clean themselves — the factory owns versioning.

### Follow-up (not yet wired, to avoid colliding with the 5 Oct reliability repair)
* `bf_ready_gate.py`: add gate `versioned` = `GIT-SNAPSHOT-LAST.json.pushed == true` and
  `commit` newer than the slice's last served change; required for P0-class slices.
* `bf_dispatch.py` prompt: mention that the factory snapshots to GitHub at reload.

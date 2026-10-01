# Content Engine — upload state + Library search

**Human status:** HOLD. Peaches light verify next. Haikal retest not issued.
**Engineering:** U1–U5, B1–B3, L1–L7 PASS on Beta `2026-10-01` (pid 60095, :8788)
**staff_ready:** false
**Prod :8787:** pid 15975 untouched
**Commit:** `9df39108a63ca1e365ee5e2a859341a4fab62fd0` on `build/wolf-command-rebuild` (local only; this repo has no remote)

## Root causes
Poster failure after FILE STORED was shown as an upload failure. Library search was not one server-side AND query, and shoot date was not kept apart from upload date. BBQ batch `bmuowp00n` is 12 stored/indexed/poster-ready rows; two filenames remain UNKNOWN.

## Repair
Lifecycle split, Retry Preview on the stored asset, server-paged Library. Prior ffmpeg commit `e0896ae` kept. Full write-up: `state/build-factory/RESULT-BF-content-engine-upload-state-library-search-20261001.md`.

## Residual
Do not mark the BBQ batch successful. Do not ask Haikal to retest until Peaches verifies this pack.

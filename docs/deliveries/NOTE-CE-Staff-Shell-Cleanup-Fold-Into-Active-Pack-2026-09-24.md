# NOTE — CE Staff Shell Cleanup folded into active pack — 2026-09-24

**Owner:** CONTENT ENGINE — STAFF SHELL CLEANUP (~17:30 WITA).  
**Fold target:** `BF-content-engine-haikal-fail-repair-20260924`  
**Cursor pid 45807:** **NOT killed** · **NOT re-prompted** · left running on soft head `f3ab8f7`.  
**No new Cursor pack / redesign pack launched.** Credit conservation ON.

## Why fold (not relaunch)

Shell cleanup is staff-surface UX debt on the same Beta CE desk the active repair pack already owns. Launching a second breadth pack would burn credits and risk colliding with uncommitted soft head work.

## ADDENDUM source of truth

`docs/deliveries/ADDENDUM-Content-Engine-Staff-Shell-Cleanup-2026-09-24.md`

Pointers also on RULE + SPEC for this run (must be present **before** Peaches final verify / before READY FOR HAIKAL RETEST).

## If Cursor EXIT before implementing shell cleanup

Peaches verify **MUST FAIL** the staff-shell criteria (header/nav cleanup, MEDIA≠CONTENT type separation per ADDENDUM, upload chrome, Library staff chrome, hide WI from primary nav, no engineering-panel chrome).

Then only:

1. **Surgical Beta fix** on `:8788`, or  
2. **Bounded same-run follow-up** inside this repair (same run id / same soft head),  

**Not** a new breadth redesign pack.

## Confirmed at fold time

- Prod `:8787` (pid often 15975) untouched  
- Beta `:8788` only  
- `staff_ready` / commissioned / telegram_retired **not** set  
- Matt FINISHED **not** pinged  

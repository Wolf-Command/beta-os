# venue_daily_closes path note — 2026-10-01T07:42:49+08:00

**Count: 0** in content_library.sqlite. ROLE-BZG-CLOSER is seated (1 active) but no nightly close has been filed.

## Why still 0
Uma close desk exists; rows are simply not being written into venue_daily_closes. Prior SoD proves kept the live table empty on purpose. This is staff/ops filing, not a missing credential.

## Is ESB fallback enough for Uma night?
**Yes for Owner pulse.** bzg_night is LIVE via authorised ESB warehouse READ (biz 2026-09-30 · finished 50 · covers 87 · grand 15,140,000 IDR), stamped theoretical consumption only; settlement remains EXTERNAL.

## Fix?
Document only this run — no obvious 1-file fix. Inventing closes would violate honesty. Optional later: staff close SOP into Uma desk.

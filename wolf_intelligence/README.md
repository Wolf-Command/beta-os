# Wolf Intelligence

Control plane for routing, shadow compare, and the Owner UI. It is not an agent, and it is not the 06:08 P0 supervisor. It runs on the Studio and dies with it. The independent off-Studio watcher is a separate component (NAS DSM task 7).

Dispatch stays in shadow unless a live submit sets both `execute=True` and `WOLF_INTELLIGENCE_LIVE_SUBMIT`. Paid API calls also need a per-call cost cap; an unset cap refuses the call. The current-system worker comes from per-job factory history. If that history is missing, the hint is UNKNOWN.

The Owner UI binds to `127.0.0.1:8799` only. POST requires `WOLF_INTELLIGENCE_UI_TOKEN`. When the token is unset, GET still serves the board and every POST returns 401. Pass and Fail also require a non-empty actor. The token is never logged.

Learning counters treat a row as human only when it has a non-empty actor, a source other than `synthetic`, and an `effective_source` that starts with `human`. Phase 4 is BUILT / SYNTHETIC TESTED. Outcome history is not rewritten; a recompute drops actor-less rows from `outcomes_human` and `human_passes`.

Tests use the standard library only:

```bash
python3 -m unittest discover -s wolf_intelligence/tests -v
```

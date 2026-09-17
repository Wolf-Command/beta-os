# Backlog — Deployed-route UI acceptance — 2026-09-17

## Incident

Matt opened `https://beta.wolfcommand.net/progress` → 404 despite git + unit tests green.

## Gap

Factory acceptance treated ephemeral HTTP Handler tests as proof of live Beta routes.

## Work landed (this slice)

- Clean aliases: `/progress`, `/uma-blu-close`, `/habitat-operator`
- `prove_deployed_ui_routes.py` against real `:8788`
- RULE + Build-Factory MUST gate
- `beta_restart.py` (LaunchAgent only)

## Follow-ups (optional)

- Wire prove into CI/nightly when Mac worker available
- Extend prove matrix for other clean UI aliases as they are added
- Consider LaunchAgent reload hook after `serve_beta.py` file mtime change (careful; do not thrash)

## Out of scope

Production `:8787`, wolf-system, Metricool writes, Habitat planner data.

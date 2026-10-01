# Maintenance / PM (ATRIUM-OPS-MAINTENANCE-PM-1)

Beta-only work order + preventive maintenance store.

- `maintenance_pm.sqlite` — runtime DB (local; eng-prove)
- `amg-preventive-maintenance.seed.json` — read-only mirror of V1 19-task schedule

Asset SoT remains CAP-MSC-01 `/api/msc/assets`. Do not invent a second register.
Cloudbeds / ClickUp / Notion / Telegram sinks stay RETIRED. No auto room blocks.
`staff_ready` stays false until human commission.

# CURSOR MISSION — Matt Progress Dashboard v1

Implement exactly: `docs/deliveries/GROK-PLAN-PROGRESS-DASHBOARD-2026-09-17.md`

Also honour dirty-tree note: `docs/deliveries/DIRTY-TREE-CLASSIFICATION-2026-09-17.md` — preserve all listed dirty paths; do not reset/stash/delete.

## Hard rules
- Workspace `/Users/wolfterminal/beta-os` branch `build/wolf-command-rebuild`
- Beta only · Owner (PERS-MATT) only · staff 403
- BUILT ≠ COMMISSIONED ≠ LIVE everywhere
- No invented thresholds / fake % precision · label ESTIMATED
- No ESB/Metricool/Production writes
- No Habitat content_planner mutations
- Do not edit Phase2.6 dirty WIP files
- Commit when green

## Deliverables
1. progress_read_model + overlay with provenance
2. Owner-only API + progress.html + /progress route + Owner nav link
3. All menu views Matt specified (Empire default)
4. Habitat + Uma Blu vertical status accurate from real state/docs
5. Tests covering Matt mandatory list
6. Canon PROGRESS-DASHBOARD.md including calculation English
7. Leave unrelated dirty files untouched; report tree state honestly

## Success
New tests PASS · Core regressions PASS · Owner can open /progress · staff blocked

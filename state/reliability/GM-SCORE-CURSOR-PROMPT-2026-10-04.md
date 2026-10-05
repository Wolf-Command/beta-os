# GM-SCORE — Owner Home headline plus register page

You are working in /Users/wolfterminal/beta-os. Do not commit. Do not push. Do not touch prod. Do not reload Beta. Do not edit or copy catalog/content_library.sqlite or catalog/backups. Do not mutate close VDC-470e741f. Do not print process arguments.

Approved scope: Owner Home headline plus register page, projection of the frozen register only.

The frozen register is already on disk. Do not edit it. Do not pretty-rewrite tasks. Do not change task states. Do not add or remove tasks.

Path (read this file; it is the only source of numbers):
/Users/wolfterminal/beta-os/state/god-mode/GOD-MODE-REGISTER-2026-10-04.json

Headline fields to read from that file, not re-typed and not from any second source:
- numerator_complete (must be 0)
- denominator (must be 43)
- percent (0.0)
- rollup (complete, ready_for_human_test, in_progress, blocked_externally, not_started, discovered)
- movement.today (0)
- by_system[].system, complete, total

Do NOT display the top-level "fraction" string. It currently says "0/45" and disagrees with denominator 43, numerator_complete 0, and the 43 tasks. The headline is numerator_complete / denominator from those fields.

## What to build

Find the running Owner Home page (the one served at /wolf, title Owner Command). Add a prominent headline the owner sees without scrolling past it if the page already has a top: GOD MODE, 0 / 43 COMPLETE, 0.0%, and +0 TODAY. The numbers must be read from the JSON file at request time or embedded from that file in the same change. Do not hardcode a second source. If you embed, the embed must match the file exactly and the page must say the figure is the frozen register.

Clicking the headline opens GOD MODE COMPLETION, a simple register. Filters: ALL, COMPLETE, READY FOR HUMAN TEST, IN PROGRESS, BLOCKED, NOT STARTED, and by business/system. IN PROGRESS means DESIGNED, BUILT, DEPLOYED, REAL DATA, or ENGINEERING PROVED. COMPLETE means HUMAN COMMISSIONED only.

Each row: ID, task, business/system, current state. Details on click: owner/worker, real data, deployed, human test, blocker, last movement, evidence.

Also show the pipeline counts from the file and by-system complete/total. Totals must come from the file, not be re-typed.

Plain language. No engineering jargon on the headline.

Do not change task states. Do not add or remove tasks. Do not touch Daily Close, petty cash, recipes, finance pages, prod, or the protected close.

Do not copy the live catalog sqlite. Tests, if any, use a tiny temp file or no database. If a test would copy the live catalog, skip the test and say so.

Do not reload Beta. HTML is read from disk per request. If you must change Python to serve a new route, stop before reload and write that in the result file. Peaches will reload only after checking prod and the close.

Do not commit.

Write state/reliability/GM-SCORE-RESULT-2026-10-04.md with status, files changed, and whether a reload is required.

Task objects in the register use these keys: id, task, business_system, state, owner_worker, real_data, deployed, human_test, blocker, last_movement, evidence. Map the detail view to those keys. Do not invent tasks.

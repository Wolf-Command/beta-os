# GROK PLAN — Owner Commissioning Queue P0 — 2026-09-22

**Run:** BF-wolf-owner-commissioning-queue-p0-20260922
**Bound:** Beta :8788 only. Production sacred.
**Authority:** RULE-Wolf-Overnight-Owner-Commissioning-2026-09-22.md + Progress existing read model.

## Goal
Permanent ordered MY COMMISSIONING / Needs Matt queue INSIDE Progress (progress.html + progress_read_model.py + Work Items / CR). Not a new task database.

## Card fields
TASK (plain English), PRIORITY P0/P1/P2, BUSINESS, PERSON TO TEST, OPEN (deep link), DO THIS (max simple numbered steps), CHECK, FEEDBACK (PASS / PROBLEM / CONFUSING / MISSING / WRONG DATA / PERMISSION PROBLEM / MOBILE PROBLEM / OTHER), SCREENSHOT/EVIDENCE upload with provenance, COMMENT, SUBMIT.

## On submit
Immutable evidence row (task, person, timestamp, surface, route, business, capability, criterion, feedback, files).
PASS -> evaluate human-test criterion; close if satisfied; recalc derived state.
PROBLEM* -> CR/Work Item -> engineering lane -> Beta fix -> auto RETEST card for same person.
Matt must not manage engineering tickets.

## Derive queue from real state
Seed from CR + capability + NAS staff_ready=false + Global Nav Owner review + Smart Upload regression + Devi Uma mobile + Amanda GGV + AMG ops + Needs You + Integration Health.
Skip known-broken. Order: highest value human commission first.
Haikal NAS Library human test = staff Needs; Matt Global Nav Owner review = Needs Matt.

## Counters (derived)
NEEDS MATT, NEEDS STAFF, READY TO TEST, RETEST, BLOCKED EXTERNAL, ENGINEERING, COMMISSIONED.

## Prove
Desktop + mobile Progress commissioning UX; email identity; RBAC; direct route; evidence upload; PASS and PROBLEM paths; retest generation; history.
Honesty: proven=false ready=false. No invent HUMAN COMMISSIONED without submit evidence.

## Out
Production mutate, ClickUp/Telegram, fake Haikal PASS, inventing SYSTEM %.

EXIT: SUCCESS with PASS=/FAIL=0 and GROK-REVIEW written.

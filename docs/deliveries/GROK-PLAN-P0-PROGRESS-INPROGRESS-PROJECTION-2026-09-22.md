# GROK PLAN — P0 Progress In progress projection — 2026-09-22

## Class
FIX / projection honesty. Do NOT inflate SYSTEM%. SYSTEM 25.5% may stay.

## Problem
Owner Progress shows In progress **0** while compressed factory has ACTIVE lanes / completed packs. Silent zero is unacceptable.

## Required
1. Find canonical source for Progress Open / In progress counts (Completion Register + factory state).
2. If factory ACTIVE / WAITING_CURSOR / GROK_REVIEW / IN_FLIGHT exists → In progress ≥ 1 OR show PROJECTION STALE loud.
3. Surface (Owner Progress, not eng dump): current active pack, queued packs, recently completed, blocked human branches (Devi/Habitat), last factory advance.
4. Tests: fixture with ACTIVE factory run → In progress not 0; empty factory → honest 0 with no stale lie.
5. No second scoring table. No invent SYSTEM%. Beta only.

## EXIT
EXIT: SUCCESS with proof.

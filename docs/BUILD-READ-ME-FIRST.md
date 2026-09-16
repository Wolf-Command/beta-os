# BUILD READ ME FIRST

**STOP. Read this before you change anything in Beta.**

Applies to every human and every AI builder (Peaches, Grok Bot, Cursor, and anyone else).

---

## Before you modify Beta

You MUST read, in order:

1. `RULE-Software-First-Agent-Scarcity-2026-09-16.md`
2. `RULE-Beta-Construction-Production-Sacred-2026-09-16.md`
3. Wolf Command Master Specification (when present in the build workspace)
4. Master Build Dashboard (when available in the build workspace)

If a required document is missing, **stop and report**. Do not invent architecture.

Work only under:

`/Users/wolfterminal/beta-os/`

unless Matt explicitly approves another path.

---

## Standing principles (read aloud)

```
SOFTWARE FIRST.
AGENTS RARE.
REUSE WOLF CORE.
ONE SOURCE OF TRUTH.
DETERMINISTIC CONTROLS.
AI FOR REASONING.
PRODUCTION IS SACRED.
CLAIMED ≠ VERIFIED.
```

Also:

**DESIGNED ≠ BUILT ≠ TESTED ≠ LIVE.**

---

## Hard stops

* Do not create a new agent to solve an engineering problem software can solve.
* Do not mutate production (DB, DNS, Cloudflare, secrets, jobs, Mac prod services, NAS, B2, live integrations).
* Do not use production write credentials from Beta.
* Do not write from Beta to production databases, services, storage, queues, APIs, or integrations.
* Do not auto-deploy Beta to Production.
* Do not create unnecessary temporary domains.
* Do not manually copy random working components between environments.

---

## Default stack

**DATA → DETERMINISTIC SOFTWARE → TOOLS → SKILLS → REASONING → HUMAN**

Not:

**NEW REQUIREMENT → NEW AGENT**

---

## Evidence

Prove claims with paths, hashes, tests, and process checks.

CLAIMED ≠ VERIFIED.

---

Locked ★ 16 Sep 2026 Matthew. Read before every Beta change.

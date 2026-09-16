# WOLF COMMAND — BETA CONSTRUCTION / PRODUCTION SACRED

## Status

MANDATORY CONSTITUTIONAL BUILD RULE

Applies to:

* Peaches
* Grok Bot
* Cursor
* all AI coding/review systems
* all future Wolf Command developers
* all Wolf applications and modules

Canon path (Beta construction site): `/Users/wolfterminal/beta-os/docs/RULE-Beta-Construction-Production-Sacred-2026-09-16.md`

Locked by Matthew 16 Sep 2026.

---

## Core Rule

**BETA IS THE CONSTRUCTION SITE.**

**CURRENT PRODUCTION IS SACRED.**

We will build the new Wolf Command architecture entirely in the existing Beta environment/domain.

We may progressively bring completed capabilities **LIVE-IN-BETA** while other capabilities continue being built.

---

## 1. Existing Beta only

Build in the existing Beta environment.

Do NOT create multiple temporary domains or copy working modules between domains unless there is a specific technical reason approved by Matt.

Do NOT manually copy random working components between environments.

---

## 2. Production is sacred

Do NOT mutate the current production Wolf system, including:

* production databases
* production DNS
* production Cloudflare configuration
* production secrets
* production jobs / automations
* Mac Studio production services
* NAS production services
* Backblaze production data
* live external integrations

**Infrastructure counts as production:** DNS, Cloudflare, Mac services, NAS, B2, secrets, jobs, integrations, and databases.

Production may be inspected **READ-ONLY** when required to understand the existing system.

Any future production migration requires a **separate explicit Matt approval**.

Production is **read-only** during this rebuild unless Matt explicitly approves a specific production mutation.

---

## 3. LIVE-IN-BETA

Beta capabilities may progressively become **LIVE-IN-BETA** while the rest of Wolf continues being built.

LIVE-IN-BETA means the capability is real and usable in Beta. It does **not** mean production.

---

## 4. No production write credentials from Beta

No Beta code may use production **write** credentials.

No Beta code may write to:

* production databases
* production services
* production storage
* production queues
* production APIs
* production integrations

Production data required for development should use **read-only** access or **sanitised / test data** as appropriate.

---

## 5. Promotion is a controlled release

Promotion from Beta to Production is a **future controlled release process** requiring Matt approval.

There is **no automatic Beta → Production deployment**.

Production promotion requires:

* verified tests
* permissions / security checks
* migration plan
* backup
* rollback plan
* Matt approval

---

## 6. Evidence law

**CLAIMED ≠ VERIFIED.**

**DESIGNED ≠ BUILT ≠ TESTED ≠ LIVE.**

Do not tell anyone the environment is isolated, safe, or done unless you have actually proved it with evidence (paths, hashes, process checks, tests).

---

## 7. Build gate

Before Grok Bot or Cursor writes any new Wolf architecture code:

1. Read this rule.
2. Read `RULE-Software-First-Agent-Scarcity-2026-09-16.md`.
3. Read `BUILD-READ-ME-FIRST.md`.
4. Work only under `/Users/wolfterminal/beta-os/` unless Matt approves a different path.
5. Do not touch production infrastructure.

---

## Final principle

**Build in Beta.**

**Protect production.**

**Promote only with Matt approval, tests, backup, and rollback.**

Locked ★ 16 Sep 2026 Matthew. MANDATORY.

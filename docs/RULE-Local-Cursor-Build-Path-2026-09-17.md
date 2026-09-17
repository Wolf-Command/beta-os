# RULE — Local Cursor Build Path (LOCKED)

**Locked ★ 17 Sep 2026 Matthew.**

## Decision

We are **NOT** creating a Git remote at this stage.

**Primary coding environment:** Cursor Local Agent / My Machine on `Wolfs-Mac-Studio`

**Local Beta repository:** canonical construction repository

**Path:** `/Users/wolfterminal/beta-os/`

**Branch:** `build/wolf-command-rebuild`

**Remote SCM:** NOT YET REQUIRED

Cursor Cloud Agents that require an SCM URL are **NOT** part of the required factory right now. Do not create a remote only to satisfy Cloud Agents.

## Factory architecture

```
MATT
→ PEACHES
→ GROK BOT
→ CURSOR LOCAL AGENT
→ TESTS
→ GROK REVIEW / RED TEAM
→ CURSOR FIXES
→ PEACHES VERIFY
→ MATT
```

## Peaches (Architecture Governor / CoS)

* May invoke/control the Cursor local agent.
* May provide Cursor the approved mission.
* May inspect evidence.
* Must **NOT** substitute Peaches Shell coding for Cursor application implementation.
* Implementation work needs actual Cursor execution evidence.

## Grok Bot (Engineering Lead / Build Planner / Code Reviewer)

* Plans the implementation **before** Cursor writes.
* After Cursor finishes: reviews the actual Git diff and implementation.
* Performs security / red-team review.
* If fixes are needed: Grok specifies findings → Cursor performs fixes.
* Build-time engineering support only — **not** a new Wolf runtime agent.

## Git law (Beta local)

Local Git remains authoritative for the Beta build for now. **No remote.**

Every coding slice must:

1. begin from a **CLEAN** working tree
2. use the approved branch `build/wolf-command-rebuild`
3. produce a reviewed diff
4. pass tests
5. produce **one** bounded commit
6. end **CLEAN**

A private remote may be introduced later only for a clear benefit (off-machine backup, collaboration, formal PR, CI, disaster recovery). That decision is separate from any single slice (including Authority Limits).

## Scope of this document

Documentation / build-governance only. Does not itself implement application features.

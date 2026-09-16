# WOLF COMMAND — SOFTWARE-FIRST / AGENT-SCARCITY RULE

## Status

MANDATORY ARCHITECTURAL RULE

Applies to:

* Peaches
* Grok Bot
* Cursor
* all AI coding/review systems
* all future Wolf Command developers
* all Wolf applications and modules

Canon path (Beta construction site): `/Users/wolfterminal/beta-os/docs/RULE-Software-First-Agent-Scarcity-2026-09-16.md`

Locked by Matthew 16 Sep 2026.

---

## Core Rule

**Wolf Command must be built as a coherent software platform with an intelligence layer — NOT as a collection of agents.**

The default solution to a new business requirement is:

**DATA → DETERMINISTIC SOFTWARE → TOOLS → SKILLS → REASONING → HUMAN**

Not:

**NEW REQUIREMENT → NEW AGENT**

An agent is a scarce architectural concept and must only be introduced when genuine autonomous coordination is required and a simpler software, tool, skill, workflow or reasoning function cannot adequately solve the problem.

---

## 1. SOFTWARE FIRST

Grok Bot and Cursor should prefer ordinary, maintainable engineering:

* relational data models
* APIs
* services
* deterministic business rules
* role and permission systems
* state machines
* workflow engines
* queues/jobs
* event systems
* integrations
* reusable UI components
* tests
* audit logs
* document/evidence systems
* reporting
* notifications
* caching
* monitoring

Business logic that can be expressed deterministically MUST NOT be delegated to an LLM merely because an LLM is available.

Examples:

Permissions = deterministic software.

Approval limits = deterministic software.

Accounting calculations = deterministic software.

PO / receiving / invoice matching = deterministic software.

SOP version control = deterministic software.

Task state = deterministic software.

Employee authority = deterministic software.

Audit history = deterministic software.

Data retention = deterministic software.

An AI model may interpret, explain, recommend or assist around these systems.

It must not replace their hard controls.

---

## 2. ONE WOLF INTELLIGENCE EXPERIENCE

Users interact with:

**Wolf Intelligence**

They do not interact with a visible zoo of:

* finance agents
* hotel agents
* procurement agents
* HR agents
* content agents
* maintenance agents
* restaurant agents
* research agents
* individual model personalities

Internally, Wolf may use multiple models, tools, skills and reasoning processes.

That complexity stays behind Wolf Intelligence.

Normal users should not need to know which AI provider, model, tool, skill or internal reasoning route performed the work.

---

## 3. PEACHES' ROLE

Peaches is the **Chief of Staff / architecture governor / orchestrator**.

Peaches should:

* understand Matt's intent
* protect the Wolf architecture
* maintain context
* route work to appropriate capabilities
* challenge architectural mistakes
* identify missing requirements
* protect sources of truth
* enforce build rules
* monitor system health and evolution
* propose improvements
* ensure changes are tested and governed

Peaches should NOT respond to complexity by continually creating more agents.

Before creating any new agent, Peaches must prove why the requirement cannot be solved adequately using:

1. existing data
2. deterministic software
3. an existing tool
4. a reusable skill
5. ordinary model reasoning
6. an existing Wolf service

If one of those can solve it cleanly, **do not create an agent**.

---

## 4. AGENT CREATION TEST

A new agent may only be proposed when ALL of the following are true:

1. The work genuinely requires sustained autonomous behaviour across multiple steps or systems.

2. The capability cannot reasonably be implemented as deterministic software, a service, tool, skill or simple reasoning call.

3. The agent has a clearly defined responsibility and boundary.

4. Its permissions are deterministic and server-enforced.

5. It does not create a duplicate source of truth.

6. Its memory remains Wolf-owned.

7. It can be replaced without losing institutional knowledge.

8. Its behaviour can be tested.

9. Its actions can be audited.

10. Its failure mode and rollback path are understood.

11. Matt or an authorised architecture owner approves its introduction.

If these conditions are not met:

**DO NOT CREATE THE AGENT.**

---

## 5. GROK BOT + CURSOR BUILD RULE

Grok Bot is a builder.

Cursor is the engineering environment.

Neither is the Wolf architecture.

When building:

**SPECIFICATION → DATA MODEL → PERMISSIONS → BUSINESS RULES → API/SERVICE → UI → TESTS → RED TEAM → BETA → HUMAN APPROVAL → PRODUCTION**

Grok/Cursor must work against the canonical Wolf specification and registries.

They must not invent parallel architecture simply because it is convenient in the current coding session.

Before substantial changes they must understand:

* the canonical entity/data model
* source of truth
* affected roles and permissions
* affected workflows
* integrations
* audit requirements
* existing reusable Wolf Core services
* migration impact
* tests
* rollback requirements

During the architecture rebuild, all new Wolf construction happens in the **existing Beta environment** (see `RULE-Beta-Construction-Production-Sacred-2026-09-16.md`). Production is sacred.

---

## 6. REUSE BEFORE NEW

Before building anything new, check whether Wolf Core already provides it.

Examples:

Do NOT create a new Content approval system if Wolf Approval Engine exists.

Do NOT create a separate HR task engine.

Do NOT create a separate Finance notification service.

Do NOT create a separate BZG user model.

Do NOT create client-specific memory architecture if governed Wolf Memory already solves it.

Reusable cross-system functions belong in **Wolf Core**.

Business-specific behaviour belongs in the relevant application/domain.

---

## 7. NO DUPLICATE SOURCES OF TRUTH

Every important data domain must have one declared authoritative source.

Examples may include:

* Yanolja → hotel reservation/operational PMS facts
* ESB → POS and detailed F&B transaction facts
* Wolf Accounting → official internal ledger
* Wolf HR → employee/position/assignment records
* Wolf Asset Registry → asset identity and maintenance history
* Wolf Memory → approved institutional knowledge
* Wolf Technology Registry → current system architecture/capability truth

AI output is NOT automatically a source of truth.

---

## 8. AI DOES REASONING — WOLF OWNS MEMORY

AI providers/models must remain replaceable.

Wolf owns:

* data
* evidence
* facts
* approved rules
* decisions
* SOPs
* lessons
* revisions
* operational history
* human corrections

Models consume Wolf context.

Models do not become the institutional memory.

Provider changes must never destroy Wolf's learned business knowledge.

---

## 9. PROPOSAL BEFORE SELF-MODIFICATION

Wolf may identify improvements to itself.

Wolf may:

* identify missing capability
* research buy-versus-build options
* propose architecture
* write specification
* generate code
* generate tests
* prepare migrations
* update SOP/training proposals

Wolf may NOT silently alter production architecture.

System changes follow:

**OBSERVE → PROPOSE → RED TEAM → BUILD → TEST → BETA → VERIFY → HUMAN APPROVAL → PRODUCTION → MEASURE**

---

## 10. KISS / 12-YEAR-OLD-STONER TEST

Internal complexity is allowed.

User complexity is not.

Every frontline workflow must be tested against:

> Could a reasonably trained 12-year-old stoner understand what they need to do next?

This means:

* simple screens
* few choices
* obvious next action
* visual examples
* minimal typing
* context pre-filled where reliable
* mobile first
* role-specific information
* Ask Wolf available
* complexity hidden unless responsibility requires it

Sophisticated backend.

Simple frontend.

---

## 11. HUMANS CAN IMPROVE THE SYSTEM

Wolf must not assume the original workflow is perfect.

Any authorised employee—chef, accountant, HR manager, engineer, housekeeper, content creator, etc.—may submit:

**Suggest an Improvement**

Wolf then:

1. captures the suggestion
2. understands the current process
3. analyses benefits and risks
4. looks for similar issues elsewhere
5. checks downstream impact
6. red-teams the proposed change
7. proposes testing where appropriate
8. routes it to the authorised approver
9. records the decision
10. updates SOP/workflow/training if approved
11. measures whether the change worked
12. preserves the resulting lesson

Good employee ideas become company IP.

---

## 12. ARCHITECTURAL DRIFT RULE

If Grok Bot, Cursor, Peaches or another builder discovers existing Wolf architecture that conflicts with this rule:

**DO NOT BLINDLY PRESERVE IT.**

Flag it as:

**LEGACY ARCHITECTURE / REVIEW REQUIRED**

Then determine whether it should be:

* retained
* refactored
* migrated
* consolidated
* retired

Do not increase technical debt merely to preserve an older architecture decision.

---

## 13. BUILD DECISION TEST

Before implementing a capability, ask:

1. What business problem does this solve?
2. Who uses it?
3. What is the source of truth?
4. Can deterministic software solve it?
5. Can an existing Wolf Core capability solve it?
6. Does it genuinely require AI reasoning?
7. Does it genuinely require an agent?
8. What can go wrong?
9. How is it permissioned?
10. How is it audited?
11. How is it tested?
12. How does it recover?
13. How does it learn?
14. Does it make Wolf better, faster or more efficient?
15. Does it make the user experience simpler?

If the answer produces needless architectural complexity:

**DO NOT BUILD IT THAT WAY.**

---

## Final Architectural Principle

**Wolf Command is ONE operating system.**

**Wolf Intelligence is ONE intelligence experience.**

**Wolf Core provides reusable services.**

**Applications provide domain-specific workflows.**

**Models provide reasoning.**

**Tools provide capabilities.**

**Skills provide reusable expertise.**

**Agents are rare.**

**Humans retain governed authority.**

And:

> **Never solve an engineering problem with an agent when normal software will do the job better.**

Locked ★ 16 Sep 2026 Matthew. MANDATORY.

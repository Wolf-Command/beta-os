# What is left to finish Wolf Command

SYSTEM = 19.65 / 77 = 25.52% ; STAFF READY = 0 ; HUMAN COMMISSIONED = 0 ; OPERATING ADOPTION = NOT MEASURED

As of the Wave 3 Pack 5 reconciliation on 27 Sep 2026. SYSTEM is the machinery score from `state/model-c-baseline-assessments.json`. Staff readiness, human commissioning, and operating adoption are not added into it.

Priority rule: W3-P5-PRIORITY-v1. Progress dial rounds the same sum to 25.5%. That 1-decimal figure is the same credit total, not a second score.

Counts: ABSENT 1, SPECIFIED 41, BUILT 20, PROVEN 12, READY 3. Priorities: P0 12, P1 20, P2 42, P3 3.

No capability in this list is staff ready. None is human commissioned. Operating adoption is NOT MEASURED. A rendered desk is not a walk.

## Must finish in the next 6 days

P0 or P1, and the SYSTEM state is not READY. The next bar is Wolf-side work. Several of these still wait on a person for the deployed-route half. That wait is named on the item and under Waiting on a human. It is not a second copy of the capability.

### CAP-INTG-07 — Secrets & Environment Separation

- What it is: Secrets management; Dev/Beta/Prod separation; no secrets in SOPs/chats; sanitised test data preference.
- Why it matters: Wolf cannot enforce or refuse an action without this.
- Current state: SYSTEM SPECIFIED (0.05). Domain D-INTG — Integrations / Infrastructure. Priority P0. Effort L.
- Exact remaining work: Matt names the vault product. The 27 Sep 2026 search found the plaintext credential directory and no vault. Ledger stays SPECIFIED. See docs/wolf/p0/P0-CAP-INTG-07-RESULT.md.
- Work classes: cursor_build, local_deterministic, human_commissioning, owner_decision.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Locatable implementation for BUILT. PROVEN still needs deterministic tests and material red-team or review evidence.
- Six-day note: Not at BUILT. Six days does not stand in for the missing implementation.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-MSC-02 — Access & Cloudflare Posture

- What it is: Seats, doors, Access includes; Matt-owned flips preserved.
- Why it matters: Wolf cannot enforce or refuse an action without this.
- Current state: SYSTEM BUILT (0.25). Domain D-MSC — Maintenance / Security / Compliance. Priority P0. Effort M.
- Exact remaining work: The live-gate deny prove is recorded (commit 025dd13). CLOSED still needs a review note that is not this queue. The 2026-09-20 empty-framework review does not bind it. Ledger stays BUILT. Seated allow was not observed. See docs/wolf/p0/P0-CAP-MSC-02-RESULT.md.
- Work classes: local_deterministic, human_commissioning, owner_decision.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Deterministic verification plus material red-team or review evidence. BUILT is not PROVEN. A rendered desk is not that review.
- Six-day note: Deny prove exits 0. PROVEN still needs a review this pack does not supply. Ledger stays BUILT. Do not call Grok.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-CORE-01 — Organisation Registry

- What it is: Canonical Group→Entity→Brand→Location→Dept hierarchy.
- Why it matters: Wolf cannot enforce or refuse an action without this.
- Current state: SYSTEM PROVEN (0.80). Domain D-CORE — Wolf Core. Priority P0. Effort S.
- Exact remaining work: Seated allow and deny on the organisation reads under a real Cloudflare session. The unsigned deny is recorded in commit 99f5a27. There is no separate org UI page. Ledger stays PROVEN. See docs/wolf/p0/P0-CAP-CORE-01-RESULT.md.
- Work classes: local_deterministic, human_commissioning.
- Dependency: CAP-CORE-02 is READY_FOR_HUMAN. That session was not observed.
- Responsible role: Owner.
- Evidence required to close: Deployed or runtime proof on the intended Beta boundary for READY. A repository test is not a deployed-route test. A human walk is not this bar.
- Six-day note: Unsigned, spoofed, and bad-JWT callers are 403 on the eight organisation reads. A seated allow was not observed. A development-subject 200 is not that proof. Ledger stays PROVEN.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: Unsigned deny on Beta :8788 pid 64196 is recorded. DEPLOYED-ROUTE-PROOF-20260927 stays FAIL for a seated allow. No real Cloudflare Access JWT was presented. The local verifier suite is not that proof.

### CAP-CORE-03 — Role / Position / Assignment

- What it is: Jobs change without losing history.
- Why it matters: Wolf cannot enforce or refuse an action without this.
- Current state: SYSTEM PROVEN (0.80). Domain D-CORE — Wolf Core. Priority P0. Effort S.
- Exact remaining work: Runtime board prove for READY
- Work classes: local_deterministic, human_commissioning.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Deployed or runtime proof on the intended Beta boundary for READY. A repository test is not a deployed-route test. A human walk is not this bar.
- Six-day note: Deployed-route bar is open. Unsigned Beta stays fail-closed. A development-subject 200 is not that proof.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-CORE-04 — Permission & Authority Engine

- What it is: Deterministic server-enforced RBAC.
- Why it matters: Wolf cannot enforce or refuse an action without this.
- Current state: SYSTEM PROVEN (0.80). Domain D-CORE — Wolf Core. Priority P0. Effort S.
- Exact remaining work: Full seat-matrix deployed prove not re-run this audit
- Work classes: local_deterministic, human_commissioning.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Deployed or runtime proof on the intended Beta boundary for READY. A repository test is not a deployed-route test. A human walk is not this bar.
- Six-day note: Deployed-route bar is open. Unsigned Beta stays fail-closed. A development-subject 200 is not that proof.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-CORE-05 — Authority Limits Evaluator

- What it is: Amount/scope limits on actions.
- Why it matters: Wolf cannot enforce or refuse an action without this.
- Current state: SYSTEM PROVEN (0.80). Domain D-CORE — Wolf Core. Priority P0. Effort S.
- Exact remaining work: The P0 queue row is CLOSED. Commit fcae665 denies an action when the catalog copy has no authority-limit row, and live org_authority_limits stayed 0. That 0 is the row count, not a tolerance. Ledger stays PROVEN. The broader Beta runtime prove that would raise READY was not observed. See docs/wolf/p0/P0-CAP-CORE-05-RESULT.md. Staff ready stays no.
- Work classes: local_deterministic, human_commissioning, owner_decision.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: The P0 closure test is the empty-table deny plus live count 0. That test passed. Raising the ledger to READY still wants a broader runtime prove on Beta. That prove was not observed. A repository test is not a seated session. A human walk is not this bar.
- Six-day note: The empty-table deny exits 0. Commit fcae665. Live org_authority_limits stayed 0. Unsigned callers are 403 on Beta :8788 pid 64196. A seated check was not observed. Ledger stays PROVEN. Do not insert a limit.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: Unsigned deny on Beta :8788 pid 64196 is recorded for the authority check and the limits list. DEPLOYED-ROUTE-PROOF-20260927 stays FAIL for a seated allow. No real Cloudflare Access JWT was presented. The empty-table deny is not that seated proof.

### CAP-CORE-06 — Work Items / Promises / Decisions

- What it is: Material promises leave a defensible trail.
- Why it matters: Wolf cannot enforce or refuse an action without this.
- Current state: SYSTEM PROVEN (0.80). Domain D-CORE — Wolf Core. Priority P0. Effort S.
- Exact remaining work: Seated GET /api/core/work-items under a real Cloudflare session. The temporary trail is recorded in commit 2229b21. Live core_work_items stayed 0, so the read must match an empty list. Do not create a live work item to fill it. Ledger stays PROVEN.
- Work classes: local_deterministic, human_commissioning.
- Dependency: CAP-CORE-02 is READY_FOR_HUMAN. That session was not observed.
- Responsible role: Owner.
- Evidence required to close: The Beta status and count under the real session, matching the stored empty list. The temporary trail is not that read. A human walk is not this bar.
- Six-day note: One item on a deleted catalog copy walked OPEN, IN_PROGRESS, BLOCKED, IN_PROGRESS, COMPLETED, VERIFIED. Commit 2229b21. Unsigned callers are 403 on Beta :8788 pid 64196. A seated read was not observed. Ledger stays PROVEN.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-CORE-07 — Approval Engine

- What it is: Human authority for material decisions; Dual Approval is a requirement class inside this capability when policy demands two persons.
- Why it matters: Wolf cannot enforce or refuse an action without this.
- Current state: SYSTEM PROVEN (0.80). Domain D-CORE — Wolf Core. Priority P0. Effort S.
- Exact remaining work: Seated GET /api/core/approvals under a real Cloudflare session. The copy read is recorded in commit ab4af72. Live core_approval_requests stayed 0, so the read must match an empty list. Do not create a request to fill it. A wide production policy pack was not authored. GPO-HABITAT-CONTENT-PUBLISH and the six stored decisions are not that pack. Ledger stays PROVEN.
- Work classes: local_deterministic, human_commissioning, owner_decision.
- Dependency: The queue lists CAP-CORE-06. That seated read was not observed. This slice does not use the work-item trail.
- Responsible role: Owner.
- Evidence required to close: The Beta status and count under the real session, matching the stored empty request list, and a wide production policy pack only if Matt authored it. The copy read is not that session. A human walk is not this bar.
- Six-day note: The copy read lists zero requests for PERS-MATT and inserts no policy. Commit ab4af72. Live core_approval_requests stayed 0. Unsigned callers are 403 on Beta :8788 pid 64196. A seated read was not observed. Ledger stays PROVEN.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: Unsigned deny on Beta :8788 pid 64196 is recorded for the approval list, one missing id, and unsigned POST. DEPLOYED-ROUTE-PROOF-20260927 stays FAIL for a seated allow. No real Cloudflare Access JWT was presented. The copy read is not that seated proof.

### CAP-CORE-08 — Segregation of Duties

- What it is: Conflicting duties cannot combine end-to-end.
- Why it matters: Wolf cannot enforce or refuse an action without this.
- Current state: SYSTEM PROVEN (0.80). Domain D-CORE — Wolf Core. Priority P0. Effort S.
- Exact remaining work: Broader finance SoD live packs for READY
- Work classes: local_deterministic, human_commissioning.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Deployed or runtime proof on the intended Beta boundary for READY. A repository test is not a deployed-route test. A human walk is not this bar.
- Six-day note: Deployed-route bar is open. Unsigned Beta stays fail-closed. A development-subject 200 is not that proof.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-CORE-09 — Evidence Requirements

- What it is: Mandatory evidence before approve/live.
- Why it matters: Wolf cannot enforce or refuse an action without this.
- Current state: SYSTEM PROVEN (0.80). Domain D-CORE — Wolf Core. Priority P0. Effort S.
- Exact remaining work: Universal evidence packs on all material actions for READY
- Work classes: local_deterministic, human_commissioning.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Deployed or runtime proof on the intended Beta boundary for READY. A repository test is not a deployed-route test. A human walk is not this bar.
- Six-day note: Deployed-route bar is open. Unsigned Beta stays fail-closed. A development-subject 200 is not that proof.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-CORE-10 — Exception / Override Governance

- What it is: Break-glass logged and reviewable.
- Why it matters: Wolf cannot enforce or refuse an action without this.
- Current state: SYSTEM PROVEN (0.80). Domain D-CORE — Wolf Core. Priority P0. Effort S.
- Exact remaining work: Operating exception review cadence for READY
- Work classes: local_deterministic, human_commissioning.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Deployed or runtime proof on the intended Beta boundary for READY. A repository test is not a deployed-route test. A human walk is not this bar.
- Six-day note: Deployed-route bar is open. Unsigned Beta stays fail-closed. A development-subject 200 is not that proof.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-STRAT-02 — Owner Radar / Mission Control

- What it is: Pulse + Exceptions; bird's-eye until satisfied; progressive quiet. Priority discipline is a requirement of this cadence, not a separate capability.
- Why it matters: A daily operating loop, the money picture, or founder independence depends on this.
- Current state: SYSTEM BUILT (0.25). Domain D-STRAT — Strategy / Command. Priority P1. Effort M.
- Exact remaining work: CAP-bound Model C prove; Progress is not this CAP alone
- Work classes: local_deterministic, human_commissioning, owner_decision.
- Dependency: Requires CAP-CORE-01, CAP-CORE-06, CAP-CORE-07.
- Responsible role: Owner.
- Evidence required to close: Deterministic verification plus material red-team or review evidence. BUILT is not PROVEN. A rendered desk is not that review.
- Six-day note: A local prove can be attempted. PROVEN still needs the review the scoring rules require. This pack does not supply that review.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-AMG-01 — Hotel PMS Orchestration

- What it is: Wolf orchestrates staffing, tasks, intelligence, reporting from PMS facts. Adoption: Yanolja owns reservation/PMS transactional truth (CAP-INTG-01 INTEGRATE). Additional hotels = property adoption, not catalog clone.
- Why it matters: A daily operating loop, the money picture, or founder independence depends on this.
- Current state: SYSTEM SPECIFIED (0.05). Domain D-AMG — AMG. Priority P1. Effort L.
- Exact remaining work: Yanolja connector + orchestration code/tests
- Work classes: cursor_build, local_deterministic, human_commissioning, external_dependency, real_world_data_integration.
- Dependency: Requires CAP-INTG-01.
- Responsible role: ROLE-AMG-GM.
- Evidence required to close: Locatable implementation for BUILT. PROVEN still needs deterministic tests and material red-team or review evidence.
- Six-day note: Not at BUILT. Six days does not stand in for the missing implementation.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-AMG-04 — Daily Hotel Operating State

- What it is: Machine-generated daily ops (occupancy, ARR, arrivals/departures, OOO, forecast); housekeeping/room queues as requirements under this capability.
- Why it matters: A daily operating loop, the money picture, or founder independence depends on this.
- Current state: SYSTEM SPECIFIED (0.05). Domain D-AMG — AMG. Priority P1. Effort L.
- Exact remaining work: Machine-generated daily ops
- Work classes: cursor_build, local_deterministic, human_commissioning.
- Dependency: Requires CAP-INTG-01, CAP-AMG-01.
- Responsible role: ROLE-AMG-GM.
- Evidence required to close: Locatable implementation for BUILT. PROVEN still needs deterministic tests and material red-team or review evidence.
- Six-day note: Not at BUILT. Six days does not stand in for the missing implementation.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-INTG-02 — ESB Connector

- What it is: F&B sales/inventory/ops facts into Wolf. Adoption: ESB owns transactional truth.
- Why it matters: A daily operating loop, the money picture, or founder independence depends on this.
- Current state: SYSTEM BUILT (0.25). Domain D-INTG — Integrations / Infrastructure. Priority P1. Effort M.
- Exact remaining work: Full ESB connector CAP + contract tests
- Work classes: local_deterministic, human_commissioning, external_dependency, real_world_data_integration.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Deterministic verification plus material red-team or review evidence. BUILT is not PROVEN. A rendered desk is not that review.
- Six-day note: A local prove can be attempted. PROVEN still needs the review the scoring rules require. This pack does not supply that review.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-BZG-01 — F&B POS Orchestration

- What it is: Wolf controls intelligence, finance, procurement, risk and cross-system workflows from POS facts. Adoption: ESB owns detailed F&B stock/transaction truth (CAP-INTG-02 INTEGRATE).
- Why it matters: A daily operating loop, the money picture, or founder independence depends on this.
- Current state: SYSTEM BUILT (0.25). Domain D-BZG — BZG. Priority P1. Effort M.
- Exact remaining work: Full POS orchestration + ESB connector maturity
- Work classes: local_deterministic, human_commissioning, external_dependency, real_world_data_integration.
- Dependency: Requires CAP-INTG-02.
- Responsible role: ROLE-BZG-FB-OPS-LEAD.
- Evidence required to close: Deterministic verification plus material red-team or review evidence. BUILT is not PROVEN. A rendered desk is not that review.
- Six-day note: A local prove can be attempted. PROVEN still needs the review the scoring rules require. This pack does not supply that review.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-INTG-04 — Bank Statement Connector

- What it is: Statement file import path for finance reconcile.
- Why it matters: A daily operating loop, the money picture, or founder independence depends on this.
- Current state: SYSTEM BUILT (0.25). Domain D-INTG — Integrations / Infrastructure. Priority P1. Effort M.
- Exact remaining work: CAP-bound connector tests
- Work classes: local_deterministic, human_commissioning, external_dependency, real_world_data_integration.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Deterministic verification plus material red-team or review evidence. BUILT is not PROVEN. A rendered desk is not that review.
- Six-day note: A local prove can be attempted. PROVEN still needs the review the scoring rules require. This pack does not supply that review.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-FIN-02 — Bank Statement Ingest & Reconcile

- What it is: Weekly/monthly statement upload→reconcile until proven bank APIs. Adoption: Banks own account truth; Wolf ingests files (CAP-INTG-04).
- Why it matters: A daily operating loop, the money picture, or founder independence depends on this.
- Current state: SYSTEM BUILT (0.25). Domain D-FIN — Finance / Accounting. Priority P1. Effort M.
- Exact remaining work: CAP-bound tests + connector honesty prove
- Work classes: local_deterministic, human_commissioning, external_dependency, real_world_data_integration, owner_decision.
- Dependency: Requires CAP-INTG-04.
- Responsible role: Owner.
- Evidence required to close: Deterministic verification plus material red-team or review evidence. BUILT is not PROVEN. A rendered desk is not that review.
- Six-day note: A local prove can be attempted. PROVEN still needs the review the scoring rules require. This pack does not supply that review.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-FIN-01 — Wolf Accounting Core

- What it is: Official accounting per legal entity + group mapping for consolidation.
- Why it matters: A daily operating loop, the money picture, or founder independence depends on this.
- Current state: SYSTEM BUILT (0.25). Domain D-FIN — Finance / Accounting. Priority P1. Effort M.
- Exact remaining work: Deterministic Core tests + red-team as Model C CAP
- Work classes: local_deterministic, human_commissioning, owner_decision.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Deterministic verification plus material red-team or review evidence. BUILT is not PROVEN. A rendered desk is not that review.
- Six-day note: A local prove can be attempted. PROVEN still needs the review the scoring rules require. This pack does not supply that review.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-FIN-03 — Entity Finance Boards

- What it is: Per-entity finance operating surfaces (GGV/Atrium/Uma adoption). Adoption: Replaces former Atrium Finance Wire as AMG-specific capability.
- Why it matters: A daily operating loop, the money picture, or founder independence depends on this.
- Current state: SYSTEM BUILT (0.25). Domain D-FIN — Finance / Accounting. Priority P1. Effort M.
- Exact remaining work: Shared CAP prove matrix all entities
- Work classes: local_deterministic, human_commissioning, owner_decision.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Deterministic verification plus material red-team or review evidence. BUILT is not PROVEN. A rendered desk is not that review.
- Six-day note: A local prove can be attempted. PROVEN still needs the review the scoring rules require. This pack does not supply that review.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-FIN-05 — Management Reporting

- What it is: P&L, BS, cash flow, trial balance, management accounts; TARGET≠ACTUAL vs margin goals.
- Why it matters: A daily operating loop, the money picture, or founder independence depends on this.
- Current state: SYSTEM SPECIFIED (0.05). Domain D-FIN — Finance / Accounting. Priority P1. Effort L.
- Exact remaining work: Full P&L/BS/CF management pack
- Work classes: cursor_build, local_deterministic, human_commissioning, owner_decision.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Locatable implementation for BUILT. PROVEN still needs deterministic tests and material red-team or review evidence.
- Six-day note: Not at BUILT. Six days does not stand in for the missing implementation.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-GGV-01 — Content Machine

- What it is: Strategy→plan→asset→workflow→learn for agency and brand content.
- Why it matters: A daily operating loop, the money picture, or founder independence depends on this.
- Current state: SYSTEM BUILT (0.25). Domain D-GGV — GGV. Priority P1. Effort M.
- Exact remaining work: Full strategy-plan-asset-workflow-learn as one governed machine + tests
- Work classes: local_deterministic, human_commissioning.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: ROLE-GGV-CREATIVE-DIRECTOR.
- Evidence required to close: Deterministic verification plus material red-team or review evidence. BUILT is not PROVEN. A rendered desk is not that review.
- Six-day note: A local prove can be attempted. PROVEN still needs the review the scoring rules require. This pack does not supply that review.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-GGV-04 — Lead Triage & Speed-to-Lead

- What it is: Hot leads answered/escalated from approved facts; uncertainty escalates.
- Why it matters: A daily operating loop, the money picture, or founder independence depends on this.
- Current state: SYSTEM BUILT (0.25). Domain D-GGV — GGV. Priority P1. Effort M.
- Exact remaining work: Governed speed-to-lead capability with tests/red-team
- Work classes: local_deterministic, human_commissioning.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Deterministic verification plus material red-team or review evidence. BUILT is not PROVEN. A rendered desk is not that review.
- Six-day note: A local prove can be attempted. PROVEN still needs the review the scoring rules require. This pack does not supply that review.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-CRM-01 — Lead CRM

- What it is: Leads owned, aged, followed with client-data boundaries.
- Why it matters: A daily operating loop, the money picture, or founder independence depends on this.
- Current state: SYSTEM BUILT (0.25). Domain D-CRM — Customer / CRM / Packages. Priority P1. Effort M.
- Exact remaining work: CAP-bound tests/red-team
- Work classes: local_deterministic, human_commissioning.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Deterministic verification plus material red-team or review evidence. BUILT is not PROVEN. A rendered desk is not that review.
- Six-day note: A local prove can be attempted. PROVEN still needs the review the scoring rules require. This pack does not supply that review.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-HR-01 — People Master Record

- What it is: Canonical employee/position/assignment truth per legal entity.
- Why it matters: A daily operating loop, the money picture, or founder independence depends on this.
- Current state: SYSTEM BUILT (0.25). Domain D-HR — HR / People. Priority P1. Effort M.
- Exact remaining work: Canonical People Master per legal entity with CAP-bound tests
- Work classes: local_deterministic, human_commissioning.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Deterministic verification plus material red-team or review evidence. BUILT is not PROVEN. A rendered desk is not that review.
- Six-day note: A local prove can be attempted. PROVEN still needs the review the scoring rules require. This pack does not supply that review.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-HR-04 — Payroll Inputs

- What it is: Clean attendance/leave/pay inputs to finance.
- Why it matters: A daily operating loop, the money picture, or founder independence depends on this.
- Current state: SYSTEM SPECIFIED (0.05). Domain D-HR — HR / People. Priority P1. Effort L.
- Exact remaining work: Clean payroll-inputs CAP prove
- Work classes: cursor_build, local_deterministic, human_commissioning.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Locatable implementation for BUILT. PROVEN still needs deterministic tests and material red-team or review evidence.
- Six-day note: Not at BUILT. Six days does not stand in for the missing implementation.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-CORE-11 — SOP Factory

- What it is: Full loop: real work → evidence → learning → proposed SOP change → approval → versioning → training/acknowledgement → operational use; no silent history rewrite.
- Why it matters: A daily operating loop, the money picture, or founder independence depends on this.
- Current state: SYSTEM SPECIFIED (0.05). Domain D-CORE — Wolf Core. Priority P1. Effort L.
- Exact remaining work: Build SOP loop evidence-learn-approve-version-train-use
- Work classes: cursor_build, local_deterministic, human_commissioning.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Locatable implementation for BUILT. PROVEN still needs deterministic tests and material red-team or review evidence.
- Six-day note: Not at BUILT. Six days does not stand in for the missing implementation.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-CORE-12 — Delegation & Escalation Burn-down

- What it is: Distinguish intentional Owner authority from accidental founder dependency; delegations time-bounded; escalation burn-down measurable; supports 7/30/90/365 independence tests.
- Why it matters: A daily operating loop, the money picture, or founder independence depends on this.
- Current state: SYSTEM BUILT (0.25). Domain D-CORE — Wolf Core. Priority P1. Effort M.
- Exact remaining work: Escalation burn-down + 7/30/90/365 independence tests
- Work classes: local_deterministic, human_commissioning, owner_decision.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Deterministic verification plus material red-team or review evidence. BUILT is not PROVEN. A rendered desk is not that review.
- Six-day note: A local prove can be attempted. PROVEN still needs the review the scoring rules require. This pack does not supply that review.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

## Must commission

SYSTEM is READY. The remaining work is a human commissioning. It does not raise the row, and it is not operating adoption.

### CAP-CORE-02 — Person & Auth Identity

- What it is: Permanent Person; CF JWT → Person binding.
- Why it matters: Wolf cannot enforce or refuse an action without this.
- Current state: SYSTEM READY (1.00). Domain D-CORE — Wolf Core. Priority P0. Effort none.
- Exact remaining work: None for technical READY; adoption separate
- Work classes: human_commissioning, owner_decision.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Human commissioning evidence recorded on the commissioning register. That evidence does not change this SYSTEM row. Operating adoption is a separate measurement and is not on record.
- Six-day note: Commissioning only. Not a build. A sign-in does not raise SYSTEM.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-BZG-03 — Venue Daily Close

- What it is: Daily close + exception handover + cash chain requirements (float→bank). Adoption: Uma Blu = first adoption; Rainforest/Merah/Rooftop = future adoption — not new capabilities.
- Why it matters: A daily operating loop, the money picture, or founder independence depends on this.
- Current state: SYSTEM READY (1.00). Domain D-BZG — BZG. Priority P1. Effort none.
- Exact remaining work: Other venues are ADOPTION not SYSTEM
- Work classes: human_commissioning, owner_decision.
- Dependency: Requires CAP-INTG-02, CAP-BZG-01.
- Responsible role: ROLE-BZG-CLOSER.
- Evidence required to close: Human commissioning evidence recorded on the commissioning register. That evidence does not change this SYSTEM row. Operating adoption is a separate measurement and is not on record.
- Six-day note: Commissioning only. Not a build. A sign-in does not raise SYSTEM.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-GGV-02 — Publish Gate & Operator Loop

- What it is: Work Item + draft evidence + designated approvers + human operator loop before publish. Adoption: Habitat = first adoption; future brands reuse same capability.
- Why it matters: A daily operating loop, the money picture, or founder independence depends on this.
- Current state: SYSTEM READY (1.00). Domain D-GGV — GGV. Priority P1. Effort none.
- Exact remaining work: Human commissioning is ADOPTION; Metricool write still off
- Work classes: human_commissioning, owner_decision.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: ROLE-GGV-CREATIVE-DIRECTOR.
- Evidence required to close: Human commissioning evidence recorded on the commissioning register. That evidence does not change this SYSTEM row. Operating adoption is a separate measurement and is not on record.
- Six-day note: Commissioning only. Not a build. A sign-in does not raise SYSTEM.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

## Waiting on a human

These are acts already recorded in Day 2 and Wave 3. They are not new tasks and they are not a maturity score.

### Owner and staff sign in on Beta with Cloudflare Access

- What it is: Owner and staff sign in on Beta with Cloudflare Access
- Why it matters: Unsigned Beta routes stay fail-closed. D3 deployed-route proof is FAIL.
- Current state: CAP-CORE-02 is SYSTEM READY. No seated session was observed.
- Exact remaining work: A person with a Cloudflare seat opens Beta :8788. Do not bypass the gate.
- Dependency: Cloudflare Access. Not a code change.
- Responsible role: Owner.
- Evidence required to close: A real JWT session recorded as commissioning evidence. It does not raise SYSTEM.
- Capabilities: CAP-CORE-02, and every PROVEN row whose next bar is a deployed route.
- Source already on record: state/completion-register/DEPLOYED-ROUTE-PROOF-20260927.json.

### Open the finance books the desks are not allowed to invent

- What it is: Open the finance books the desks are not allowed to invent
- Why it matters: Owner Command and the business desks say finance UNAVAILABLE. That is not cash.
- Current state: BUILT on CAP-FIN-01
- Exact remaining work: The Owner opens the real books, or confirms they stay unavailable. Do not type a balance.
- Dependency: Owner decision. Bank files are CAP-INTG-04 and stay a connector, not a payment.
- Responsible role: Owner.
- Evidence required to close: A books source the truth register can stamp. UNAVAILABLE cleared only by that source.
- Capabilities: CAP-FIN-01, CAP-FIN-03, CAP-FIN-05.
- Source already on record: docs/wolf/wave3/W3-P1-OWNER-RESULT.md.

### Declare a source commissioned, or leave it uncommissioned

- What it is: Declare a source commissioned, or leave it uncommissioned
- Why it matters: Pack 4 left commissioned false on every source. The Needs you queue is that decision.
- Current state: Not commissioned. Wolf Core CURRENT is a store read, not a commissioning.
- Exact remaining work: The Owner accepts or refuses each source. This pack does not accept them.
- Dependency: Owner decision. Yanolja still has no reader. ESB settlement stays unavailable.
- Responsible role: Owner.
- Evidence required to close: A commissioning record per source. A file on disk is not that record.
- Capabilities: Yanolja, ESB, Wolf Core, NAS, finance ledgers, Klaviyo, Metricool.
- Source already on record: docs/wolf/wave3/W3-P4-TRUTH-RESULT.md.

### Seat a closer and, separately, write a variance policy if cash must mismatch

- What it is: Seat a closer and, separately, write a variance policy if cash must mismatch
- Why it matters: The close machine is SYSTEM READY. Nobody is on the closer position. Policy count was 0.
- Current state: SYSTEM READY. Human commissioning no. venue_daily_closes 0.
- Exact remaining work: Assign a real person to POS-BZG-CLOSER-UMA-1. Do not invent a policy to force a green close.
- Dependency: Owner decision. ESB settlement_api stays UNAVAILABLE. No payment is added.
- Responsible role: Owner.
- Evidence required to close: An active assignment on ROLE-BZG-CLOSER, plus a real variance policy only if a mismatch must be closable.
- Capabilities: CAP-BZG-03.
- Source already on record: state/completion-register/COMMISSIONING-STATE-20260927.json.

### Seat the external accountant, or leave that position empty

- What it is: Seat the external accountant, or leave that position empty
- Why it matters: POS-GGV-EXT-ACCT has no person. Finance and external accountant are one catalog role.
- Current state: Position empty. Notes desk is not the books.
- Exact remaining work: The Owner assigns a real person, or records that the seat stays empty.
- Dependency: Owner decision. Opening the books is the separate act above.
- Responsible role: Owner.
- Evidence required to close: An active assignment on POS-GGV-EXT-ACCT for a real person.
- Capabilities: CAP-FIN-03.
- Source already on record: docs/wolf/wave3/W3-P3-STAFF-RESULT.md.

### Choose the primary assignment for the person on both Content Crew and General Manager

- What it is: Choose the primary assignment for the person on both Content Crew and General Manager
- Why it matters: My Work follows the primary role. That person's primary is Content Crew. The General Manager page is not what they land on.
- Current state: CAP-CORE-03 is PROVEN. The assignment fact is already stored. It was not moved.
- Exact remaining work: The Owner keeps or changes the primary assignment. This is not an engineering rename.
- Dependency: Owner decision. People are not roles.
- Responsible role: Owner.
- Evidence required to close: The assignment row the Owner meant, still a real person, not a new demo seat.
- Capabilities: CAP-CORE-03.
- Source already on record: docs/wolf/wave3/W3-P3-STAFF-RESULT.md.

## Waiting on an external system

P0 or P1, catalog ownership INTEGRATE, and the Wolf side is not yet BUILT. Connectors that are already BUILT stay under Must finish, with the vendor named as the dependency.

### CAP-INTG-01 — Yanolja Connector

- What it is: Reservation/PMS facts into Wolf. Adoption: Yanolja owns transactional truth.
- Why it matters: A daily operating loop, the money picture, or founder independence depends on this.
- Current state: SYSTEM ABSENT (0.00). Domain D-INTG — Integrations / Infrastructure. Priority P1. Effort XL.
- Exact remaining work: Connector code/tests/contract
- Work classes: cursor_build, local_deterministic, human_commissioning, external_dependency, real_world_data_integration, owner_decision.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: An approved specification bound to this CAP-ID, then locatable implementation. A vendor existing is not that evidence.
- Six-day note: The outside system has no Wolf connector at BUILT. Do not invent its feed.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

## Can safely follow after initial launch

P2 and P3. Real capabilities. Not the control kernel and not the first daily loop. Leaving them here is not a claim they are unimportant later.

### CAP-AMG-02 — Guest Journey Operations

- What it is: Enquiry→booking→pre-arrival→arrival→stay→checkout→return memory as one journey capability.
- Why it matters: This can follow the first commissioning. It is not the kernel and not the first daily loop.
- Current state: SYSTEM SPECIFIED (0.05). Domain D-AMG — AMG. Priority P2. Effort L.
- Exact remaining work: Journey workflow implementation
- Work classes: cursor_build, local_deterministic, human_commissioning.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Locatable implementation for BUILT. PROVEN still needs deterministic tests and material red-team or review evidence.
- Six-day note: Not at BUILT. Six days does not stand in for the missing implementation.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-AMG-03 — Packages as Products

- What it is: Stay+activity packages as first-class commercial products with margin/SOP.
- Why it matters: This can follow the first commissioning. It is not the kernel and not the first daily loop.
- Current state: SYSTEM SPECIFIED (0.05). Domain D-AMG — AMG. Priority P2. Effort L.
- Exact remaining work: Package product machinery
- Work classes: cursor_build, local_deterministic, human_commissioning.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Locatable implementation for BUILT. PROVEN still needs deterministic tests and material red-team or review evidence.
- Six-day note: Not at BUILT. Six days does not stand in for the missing implementation.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-AMG-05 — Hotel Revenue & Yield

- What it is: Rates, occupancy, ADR/RevPAR visibility — machinery toward AMG ~20% operating-profit target (TARGET≠ACTUAL).
- Why it matters: This can follow the first commissioning. It is not the kernel and not the first daily loop.
- Current state: SYSTEM SPECIFIED (0.05). Domain D-AMG — AMG. Priority P2. Effort L.
- Exact remaining work: Yield machinery
- Work classes: cursor_build, local_deterministic, human_commissioning.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Locatable implementation for BUILT. PROVEN still needs deterministic tests and material red-team or review evidence.
- Six-day note: Not at BUILT. Six days does not stand in for the missing implementation.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-AMG-06 — Guest Experience Loop

- What it is: Requests/incidents with SLA/escalation; memorable service trail.
- Why it matters: This can follow the first commissioning. It is not the kernel and not the first daily loop.
- Current state: SYSTEM SPECIFIED (0.05). Domain D-AMG — AMG. Priority P2. Effort L.
- Exact remaining work: SLA/incident trail
- Work classes: cursor_build, local_deterministic, human_commissioning.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Locatable implementation for BUILT. PROVEN still needs deterministic tests and material red-team or review evidence.
- Six-day note: Not at BUILT. Six days does not stand in for the missing implementation.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-AMG-07 — Service Improvement Loop

- What it is: Review evidence → recognition/training/process improvement (reviews earned, never solicited).
- Why it matters: This is later work. It is not required for the first operating loop.
- Current state: SYSTEM SPECIFIED (0.05). Domain D-AMG — AMG. Priority P3. Effort L.
- Exact remaining work: Review-to-improve loop
- Work classes: cursor_build, local_deterministic, human_commissioning.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Locatable implementation for BUILT. PROVEN still needs deterministic tests and material red-team or review evidence.
- Six-day note: Not at BUILT. Six days does not stand in for the missing implementation.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-BZG-02 — Venue P&L & Management Rollup

- What it is: Each venue mini-business budget/KPI/dashboard; BZG Master rollup — machinery toward BZG ~20% operating-profit target (TARGET≠ACTUAL). Adoption: Venues adopt; adding venues does not clone this capability.
- Why it matters: This can follow the first commissioning. It is not the kernel and not the first daily loop.
- Current state: SYSTEM SPECIFIED (0.05). Domain D-BZG — BZG. Priority P2. Effort L.
- Exact remaining work: Venue P&L dashboards as capability
- Work classes: cursor_build, local_deterministic, human_commissioning.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Locatable implementation for BUILT. PROVEN still needs deterministic tests and material red-team or review evidence.
- Six-day note: Not at BUILT. Six days does not stand in for the missing implementation.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-BZG-04 — Inventory & Stock Control

- What it is: Theoretical vs actual variances, waste/comps/voids analysed; ESB remains transactional SoT.
- Why it matters: This can follow the first commissioning. It is not the kernel and not the first daily loop.
- Current state: SYSTEM SPECIFIED (0.05). Domain D-BZG — BZG. Priority P2. Effort L.
- Exact remaining work: Variance/waste analysis machinery
- Work classes: cursor_build, local_deterministic, human_commissioning.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Locatable implementation for BUILT. PROVEN still needs deterministic tests and material red-team or review evidence.
- Six-day note: Not at BUILT. Six days does not stand in for the missing implementation.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-BZG-05 — Central Kitchen & Shared Cost Allocation

- What it is: Evidence-based shared cost allocation across venues.
- Why it matters: This can follow the first commissioning. It is not the kernel and not the first daily loop.
- Current state: SYSTEM SPECIFIED (0.05). Domain D-BZG — BZG. Priority P2. Effort L.
- Exact remaining work: Allocation engine
- Work classes: cursor_build, local_deterministic, human_commissioning.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Locatable implementation for BUILT. PROVEN still needs deterministic tests and material red-team or review evidence.
- Six-day note: Not at BUILT. Six days does not stand in for the missing implementation.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-BZG-06 — Recipe / Cost Standards

- What it is: BOM, yield/waste, theoretical cost, menu-engineering analysis.
- Why it matters: This can follow the first commissioning. It is not the kernel and not the first daily loop.
- Current state: SYSTEM SPECIFIED (0.05). Domain D-BZG — BZG. Priority P2. Effort L.
- Exact remaining work: BOM/yield machinery
- Work classes: cursor_build, local_deterministic, human_commissioning.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Locatable implementation for BUILT. PROVEN still needs deterministic tests and material red-team or review evidence.
- Six-day note: Not at BUILT. Six days does not stand in for the missing implementation.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-BZG-07 — Review & Reputation Capture

- What it is: Reviews earned organically; signal into training/process — Wolf observes/derives, does not solicit.
- Why it matters: This is later work. It is not required for the first operating loop.
- Current state: SYSTEM SPECIFIED (0.05). Domain D-BZG — BZG. Priority P3. Effort L.
- Exact remaining work: Observe/ingest path
- Work classes: cursor_build, local_deterministic, human_commissioning.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Locatable implementation for BUILT. PROVEN still needs deterministic tests and material red-team or review evidence.
- Six-day note: Not at BUILT. Six days does not stand in for the missing implementation.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-CRM-02 — Customer Identity & Memory

- What it is: Canonical Customer ID / identity graph with confidence matching; human review when uncertain.
- Why it matters: This can follow the first commissioning. It is not the kernel and not the first daily loop.
- Current state: SYSTEM SPECIFIED (0.05). Domain D-CRM — Customer / CRM / Packages. Priority P2. Effort L.
- Exact remaining work: Identity graph
- Work classes: cursor_build, local_deterministic, human_commissioning.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Locatable implementation for BUILT. PROVEN still needs deterministic tests and material red-team or review evidence.
- Six-day note: Not at BUILT. Six days does not stand in for the missing implementation.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-CRM-03 — Package Intelligence

- What it is: Package performance, margin, demand across channels.
- Why it matters: This can follow the first commissioning. It is not the kernel and not the first daily loop.
- Current state: SYSTEM SPECIFIED (0.05). Domain D-CRM — Customer / CRM / Packages. Priority P2. Effort L.
- Exact remaining work: Implementation
- Work classes: cursor_build, local_deterministic, human_commissioning.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Locatable implementation for BUILT. PROVEN still needs deterministic tests and material red-team or review evidence.
- Six-day note: Not at BUILT. Six days does not stand in for the missing implementation.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-CRM-04 — Email Marketing Wire

- What it is: Brand email where applicable; connector honesty (Klaviyo/AC not conflated).
- Why it matters: This can follow the first commissioning. It is not the kernel and not the first daily loop.
- Current state: SYSTEM BUILT (0.25). Domain D-CRM — Customer / CRM / Packages. Priority P2. Effort M.
- Exact remaining work: Honest connector prove
- Work classes: local_deterministic, human_commissioning, external_dependency, real_world_data_integration.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Deterministic verification plus material red-team or review evidence. BUILT is not PROVEN. A rendered desk is not that review.
- Six-day note: A local prove can be attempted. PROVEN still needs the review the scoring rules require. This pack does not supply that review.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-DR-01 — Backup / Restore Testing / Disaster Recovery

- What it is: Nothing backed up until restore tested; tiered RTO/RPO; business continuity folded here as operating requirement.
- Why it matters: This can follow the first commissioning. It is not the kernel and not the first daily loop.
- Current state: SYSTEM SPECIFIED (0.05). Domain D-DR — Information / DR. Priority P2. Effort L.
- Exact remaining work: Deterministic canonical restore-drill proof for PROVEN; fresh CAP-bound Beta drill for READY
- Work classes: cursor_build, local_deterministic, human_commissioning, owner_decision.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Locatable implementation for BUILT. PROVEN still needs deterministic tests and material red-team or review evidence.
- Six-day note: Not at BUILT. Six days does not stand in for the missing implementation.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-DR-02 — Crown Jewel Protection

- What it is: Crown-jewel identification, independent failure domains, Matt-only full playbook default per Spec.
- Why it matters: This can follow the first commissioning. It is not the kernel and not the first daily loop.
- Current state: SYSTEM SPECIFIED (0.05). Domain D-DR — Information / DR. Priority P2. Effort L.
- Exact remaining work: Independent failure domains prove
- Work classes: cursor_build, local_deterministic, human_commissioning, owner_decision.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Locatable implementation for BUILT. PROVEN still needs deterministic tests and material red-team or review evidence.
- Six-day note: Not at BUILT. Six days does not stand in for the missing implementation.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-FIN-04 — Invoicing & Receivables

- What it is: Issue/correct invoices; AR trail.
- Why it matters: This can follow the first commissioning. It is not the kernel and not the first daily loop.
- Current state: SYSTEM BUILT (0.25). Domain D-FIN — Finance / Accounting. Priority P2. Effort M.
- Exact remaining work: CAP-bound tests/red-team; Amanda human prove is ADOPTION
- Work classes: local_deterministic, human_commissioning.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Deterministic verification plus material red-team or review evidence. BUILT is not PROVEN. A rendered desk is not that review.
- Six-day note: A local prove can be attempted. PROVEN still needs the review the scoring rules require. This pack does not supply that review.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-FIN-06 — Intercompany Billing

- What it is: Arms-length invoices/allocation/AR-AP between GGV↔AMG/BZG paired with CAP-GGV-06. Tax treatment deferred.
- Why it matters: This can follow the first commissioning. It is not the kernel and not the first daily loop.
- Current state: SYSTEM SPECIFIED (0.05). Domain D-FIN — Finance / Accounting. Priority P2. Effort L.
- Exact remaining work: Implementation
- Work classes: cursor_build, local_deterministic, human_commissioning.
- Dependency: Requires CAP-GGV-06.
- Responsible role: Owner.
- Evidence required to close: Locatable implementation for BUILT. PROVEN still needs deterministic tests and material red-team or review evidence.
- Six-day note: Not at BUILT. Six days does not stand in for the missing implementation.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-FIN-07 — Budget / Forecast / Cash Cadence

- What it is: Annual budget + rolling forecast + 13-week cash per entity; updates as evidence arrives.
- Why it matters: This can follow the first commissioning. It is not the kernel and not the first daily loop.
- Current state: SYSTEM SPECIFIED (0.05). Domain D-FIN — Finance / Accounting. Priority P2. Effort L.
- Exact remaining work: 13-week cash machinery
- Work classes: cursor_build, local_deterministic, human_commissioning.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Locatable implementation for BUILT. PROVEN still needs deterministic tests and material red-team or review evidence.
- Six-day note: Not at BUILT. Six days does not stand in for the missing implementation.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-FIN-08 — Profit Leakage Intelligence

- What it is: Continuous identification of waste, variance, discounts, OOO, unprofitable items, overservicing, subscription waste, preventable maintenance — supports margin targets without embedding targets in every cap.
- Why it matters: This can follow the first commissioning. It is not the kernel and not the first daily loop.
- Current state: SYSTEM SPECIFIED (0.05). Domain D-FIN — Finance / Accounting. Priority P2. Effort L.
- Exact remaining work: Leakage engine
- Work classes: cursor_build, local_deterministic, human_commissioning.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Locatable implementation for BUILT. PROVEN still needs deterministic tests and material red-team or review evidence.
- Six-day note: Not at BUILT. Six days does not stand in for the missing implementation.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-GGV-03 — Client Profitability

- What it is: Client/contract/project/deliverable P&L with staff and external cost allocation — machinery toward GGV ~70% operating-profit target (TARGET≠ACTUAL).
- Why it matters: This can follow the first commissioning. It is not the kernel and not the first daily loop.
- Current state: SYSTEM SPECIFIED (0.05). Domain D-GGV — GGV. Priority P2. Effort L.
- Exact remaining work: Build client/contract P&L allocation
- Work classes: cursor_build, local_deterministic, human_commissioning.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Locatable implementation for BUILT. PROVEN still needs deterministic tests and material red-team or review evidence.
- Six-day note: Not at BUILT. Six days does not stand in for the missing implementation.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-GGV-05 — Brand Social Performance

- What it is: Governed social performance views for brands. Adoption: Consumes Metricool via CAP-INTG-05 (INTEGRATE); does not own Metricool.
- Why it matters: This is later work. It is not required for the first operating loop.
- Current state: SYSTEM BUILT (0.25). Domain D-GGV — GGV. Priority P3. Effort M.
- Exact remaining work: Governed DERIVE views + PROVEN red-team
- Work classes: local_deterministic, human_commissioning, external_dependency, real_world_data_integration.
- Dependency: Requires CAP-INTG-05.
- Responsible role: ROLE-GGV-CREATIVE-DIRECTOR.
- Evidence required to close: Deterministic verification plus material red-team or review evidence. BUILT is not PROVEN. A rendered desk is not that review.
- Six-day note: A local prove can be attempted. PROVEN still needs the review the scoring rules require. This pack does not supply that review.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-GGV-06 — Intercompany Client Mode

- What it is: AMG/BZG as formal internal clients of GGV: service records, invoices, allocation, arms-length evidence, AR/AP treatment, audit trail. Near-term after Habitat/Uma commissioning; before Finance/Procurement maturity claim. Tax treatment OUT of this catalog.
- Why it matters: This can follow the first commissioning. It is not the kernel and not the first daily loop.
- Current state: SYSTEM SPECIFIED (0.05). Domain D-GGV — GGV. Priority P2. Effort L.
- Exact remaining work: Intercompany client mode implementation
- Work classes: cursor_build, local_deterministic, human_commissioning.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Locatable implementation for BUILT. PROVEN still needs deterministic tests and material red-team or review evidence.
- Six-day note: Not at BUILT. Six days does not stand in for the missing implementation.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-HR-02 — Hiring & Onboarding

- What it is: Manpower→recruit→onboard→probation workflows.
- Why it matters: This can follow the first commissioning. It is not the kernel and not the first daily loop.
- Current state: SYSTEM SPECIFIED (0.05). Domain D-HR — HR / People. Priority P2. Effort L.
- Exact remaining work: Workflows
- Work classes: cursor_build, local_deterministic, human_commissioning.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Locatable implementation for BUILT. PROVEN still needs deterministic tests and material red-team or review evidence.
- Six-day note: Not at BUILT. Six days does not stand in for the missing implementation.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-HR-03 — Training & Competency

- What it is: Training/acknowledgement after SOP changes; competency checks before LIVE.
- Why it matters: This can follow the first commissioning. It is not the kernel and not the first daily loop.
- Current state: SYSTEM SPECIFIED (0.05). Domain D-HR — HR / People. Priority P2. Effort L.
- Exact remaining work: Training ack machinery
- Work classes: cursor_build, local_deterministic, human_commissioning.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Locatable implementation for BUILT. PROVEN still needs deterministic tests and material red-team or review evidence.
- Six-day note: Not at BUILT. Six days does not stand in for the missing implementation.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-HR-05 — Retention & Succession Signals

- What it is: People risk and succession visibility without accidental Matt dependency.
- Why it matters: This can follow the first commissioning. It is not the kernel and not the first daily loop.
- Current state: SYSTEM SPECIFIED (0.05). Domain D-HR — HR / People. Priority P2. Effort L.
- Exact remaining work: Signals machinery
- Work classes: cursor_build, local_deterministic, human_commissioning.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Locatable implementation for BUILT. PROVEN still needs deterministic tests and material red-team or review evidence.
- Six-day note: Not at BUILT. Six days does not stand in for the missing implementation.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-INTEL-01 — Orchestration / Reasoning Surface

- What it is: One institutional WI experience; DATA→TOOLS→REASONING→SYNTHESIS→HUMAN; no agent zoo.
- Why it matters: This can follow the first commissioning. It is not the kernel and not the first daily loop.
- Current state: SYSTEM BUILT (0.25). Domain D-INTEL — Wolf Intelligence. Priority P2. Effort M.
- Exact remaining work: PROVEN needs sustained Owner use of the orchestration surface, not this slice
- Work classes: local_deterministic, human_commissioning.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Deterministic verification plus material red-team or review evidence. BUILT is not PROVEN. A rendered desk is not that review.
- Six-day note: A local prove can be attempted. PROVEN still needs the review the scoring rules require. This pack does not supply that review.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-INTEL-02 — Authorised Retrieval & Institutional Memory

- What it is: Search authorised sources; Brand Memory vs Learning Memory separated; empty≠UNKNOWN.
- Why it matters: This can follow the first commissioning. It is not the kernel and not the first daily loop.
- Current state: SYSTEM PROVEN (0.80). Domain D-INTEL — Wolf Intelligence. Priority P2. Effort S.
- Exact remaining work: READY needs sustained human workflow use, not another fixture
- Work classes: local_deterministic, human_commissioning.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Deployed or runtime proof on the intended Beta boundary for READY. A repository test is not a deployed-route test. A human walk is not this bar.
- Six-day note: Deployed-route bar is open. Unsigned Beta stays fail-closed. A development-subject 200 is not that proof.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-INTEL-03 — Provenance / Confidence / Conflict Resolution

- What it is: Evidence classes; confidence; conflict/supersession; approved truth outranks model observations.
- Why it matters: This can follow the first commissioning. It is not the kernel and not the first daily loop.
- Current state: SYSTEM PROVEN (0.80). Domain D-INTEL — Wolf Intelligence. Priority P2. Effort S.
- Exact remaining work: READY needs sustained human workflow use, not another fixture
- Work classes: local_deterministic, human_commissioning.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Deployed or runtime proof on the intended Beta boundary for READY. A repository test is not a deployed-route test. A human walk is not this bar.
- Six-day note: Deployed-route bar is open. Unsigned Beta stays fail-closed. A development-subject 200 is not that proof.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-INTEL-04 — Decision Memory

- What it is: Material decisions, options considered, approvals, outcomes preserved and recallable.
- Why it matters: This can follow the first commissioning. It is not the kernel and not the first daily loop.
- Current state: SYSTEM PROVEN (0.80). Domain D-INTEL — Wolf Intelligence. Priority P2. Effort S.
- Exact remaining work: READY needs an owner screen and a real person using recall. Not this write.
- Work classes: local_deterministic, human_commissioning.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Deployed or runtime proof on the intended Beta boundary for READY. A repository test is not a deployed-route test. A human walk is not this bar.
- Six-day note: Deployed-route bar is open. Unsigned Beta stays fail-closed. A development-subject 200 is not that proof.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-INTEL-05 — Learning / Experiments / Performance Policy

- What it is: Observation→lesson candidate→human approve→rule; performance learning; noise suppression — not a capability per persona.
- Why it matters: This can follow the first commissioning. It is not the kernel and not the first daily loop.
- Current state: SYSTEM SPECIFIED (0.05). Domain D-INTEL — Wolf Intelligence. Priority P2. Effort L.
- Exact remaining work: Approve-to-rule learning loop
- Work classes: cursor_build, local_deterministic, human_commissioning.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Locatable implementation for BUILT. PROVEN still needs deterministic tests and material red-team or review evidence.
- Six-day note: Not at BUILT. Six days does not stand in for the missing implementation.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-INTG-03 — Google Workspace Connector

- What it is: Mail/calendar/documents/auth as authorised.
- Why it matters: This can follow the first commissioning. It is not the kernel and not the first daily loop.
- Current state: SYSTEM BUILT (0.25). Domain D-INTG — Integrations / Infrastructure. Priority P2. Effort M.
- Exact remaining work: CAP-bound INTEGRATE prove pack
- Work classes: local_deterministic, human_commissioning, external_dependency, real_world_data_integration.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Deterministic verification plus material red-team or review evidence. BUILT is not PROVEN. A rendered desk is not that review.
- Six-day note: A local prove can be attempted. PROVEN still needs the review the scoring rules require. This pack does not supply that review.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-INTG-05 — Metricool Connector

- What it is: Social performance data into Wolf. Adoption: Metricool owns platform analytics.
- Why it matters: This can follow the first commissioning. It is not the kernel and not the first daily loop.
- Current state: SYSTEM BUILT (0.25). Domain D-INTG — Integrations / Infrastructure. Priority P2. Effort M.
- Exact remaining work: PROVEN red-team of connector contract
- Work classes: local_deterministic, human_commissioning, external_dependency, real_world_data_integration.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Deterministic verification plus material red-team or review evidence. BUILT is not PROVEN. A rendered desk is not that review.
- Six-day note: A local prove can be attempted. PROVEN still needs the review the scoring rules require. This pack does not supply that review.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-INTG-06 — Technology & Capability Registries

- What it is: Tech inventory, ownership of truth, lifecycle, exit conditions.
- Why it matters: This can follow the first commissioning. It is not the kernel and not the first daily loop.
- Current state: SYSTEM SPECIFIED (0.05). Domain D-INTG — Integrations / Infrastructure. Priority P2. Effort L.
- Exact remaining work: Tech inventory + exit conditions product
- Work classes: cursor_build, local_deterministic, human_commissioning.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Locatable implementation for BUILT. PROVEN still needs deterministic tests and material red-team or review evidence.
- Six-day note: Not at BUILT. Six days does not stand in for the missing implementation.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-MSC-01 — Asset & Maintenance Register

- What it is: Asset condition and maintenance tracked.
- Why it matters: This can follow the first commissioning. It is not the kernel and not the first daily loop.
- Current state: SYSTEM SPECIFIED (0.05). Domain D-MSC — Maintenance / Security / Compliance. Priority P2. Effort L.
- Exact remaining work: Register
- Work classes: cursor_build, local_deterministic, human_commissioning.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Locatable implementation for BUILT. PROVEN still needs deterministic tests and material red-team or review evidence.
- Six-day note: Not at BUILT. Six days does not stand in for the missing implementation.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-MSC-03 — Compliance Pack

- What it is: Licences, statutory, policy compliance evidence.
- Why it matters: This can follow the first commissioning. It is not the kernel and not the first daily loop.
- Current state: SYSTEM SPECIFIED (0.05). Domain D-MSC — Maintenance / Security / Compliance. Priority P2. Effort L.
- Exact remaining work: Licence/statutory evidence pack
- Work classes: cursor_build, local_deterministic, human_commissioning.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Locatable implementation for BUILT. PROVEN still needs deterministic tests and material red-team or review evidence.
- Six-day note: Not at BUILT. Six days does not stand in for the missing implementation.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-MSC-04 — Cybersecurity Baseline

- What it is: MFA, device posture, audited access; crown-jewel adjacent but not DR playbook.
- Why it matters: This can follow the first commissioning. It is not the kernel and not the first daily loop.
- Current state: SYSTEM SPECIFIED (0.05). Domain D-MSC — Maintenance / Security / Compliance. Priority P2. Effort L.
- Exact remaining work: MFA/device posture CAP
- Work classes: cursor_build, local_deterministic, human_commissioning.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Locatable implementation for BUILT. PROVEN still needs deterministic tests and material red-team or review evidence.
- Six-day note: Not at BUILT. Six days does not stand in for the missing implementation.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-MSC-05 — Documents / Records / Legal Defensibility

- What it is: Callable context-aware records; retention; legal hold; dispute chronology; contract intelligence; no silent destroy of audit evidence.
- Why it matters: This can follow the first commissioning. It is not the kernel and not the first daily loop.
- Current state: SYSTEM SPECIFIED (0.05). Domain D-MSC — Maintenance / Security / Compliance. Priority P2. Effort L.
- Exact remaining work: Callable records + legal hold CAP
- Work classes: cursor_build, local_deterministic, human_commissioning.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Locatable implementation for BUILT. PROVEN still needs deterministic tests and material red-team or review evidence.
- Six-day note: Not at BUILT. Six days does not stand in for the missing implementation.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-PROC-01 — Supplier Register & Intelligence

- What it is: Suppliers with price/quality/reliability/concentration visibility.
- Why it matters: This can follow the first commissioning. It is not the kernel and not the first daily loop.
- Current state: SYSTEM SPECIFIED (0.05). Domain D-PROC — Procurement. Priority P2. Effort L.
- Exact remaining work: Implementation
- Work classes: cursor_build, local_deterministic, human_commissioning.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Locatable implementation for BUILT. PROVEN still needs deterministic tests and material red-team or review evidence.
- Six-day note: Not at BUILT. Six days does not stand in for the missing implementation.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-PROC-02 — Purchase & Approval Flow

- What it is: Request→quotes→PO→receive→match→pay approval; SoD enforced.
- Why it matters: This can follow the first commissioning. It is not the kernel and not the first daily loop.
- Current state: SYSTEM SPECIFIED (0.05). Domain D-PROC — Procurement. Priority P2. Effort L.
- Exact remaining work: PO-match-pay with SoD
- Work classes: cursor_build, local_deterministic, human_commissioning.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Locatable implementation for BUILT. PROVEN still needs deterministic tests and material red-team or review evidence.
- Six-day note: Not at BUILT. Six days does not stand in for the missing implementation.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-PROC-03 — Payment Tracking

- What it is: Payment runs prepared/tracked; PAID only with settlement evidence. Initiation may remain outside Wolf.
- Why it matters: This can follow the first commissioning. It is not the kernel and not the first daily loop.
- Current state: SYSTEM SPECIFIED (0.05). Domain D-PROC — Procurement. Priority P2. Effort L.
- Exact remaining work: Payment runs + settlement evidence
- Work classes: cursor_build, local_deterministic, human_commissioning.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Locatable implementation for BUILT. PROVEN still needs deterministic tests and material red-team or review evidence.
- Six-day note: Not at BUILT. Six days does not stand in for the missing implementation.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-SALE-01 — Continuous Sale Evidence Pack

- What it is: Consumes evidence from Finance/HR/Legal/Ops/Compliance/Tech domains — does NOT clone those capabilities. 60 diligence cells are CONTROLS underneath.
- Why it matters: This can follow the first commissioning. It is not the kernel and not the first daily loop.
- Current state: SYSTEM SPECIFIED (0.05). Domain D-SALE — Sale Readiness. Priority P2. Effort L.
- Exact remaining work: Evidence pack automation consuming domains
- Work classes: cursor_build, local_deterministic, human_commissioning.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Locatable implementation for BUILT. PROVEN still needs deterministic tests and material red-team or review evidence.
- Six-day note: Not at BUILT. Six days does not stand in for the missing implementation.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-SALE-02 — Buyer Data Room

- What it is: Continuously updated VDR; diligence becomes controlled access.
- Why it matters: This can follow the first commissioning. It is not the kernel and not the first daily loop.
- Current state: SYSTEM SPECIFIED (0.05). Domain D-SALE — Sale Readiness. Priority P2. Effort L.
- Exact remaining work: Continuously updated VDR product
- Work classes: cursor_build, local_deterministic, human_commissioning.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Locatable implementation for BUILT. PROVEN still needs deterministic tests and material red-team or review evidence.
- Six-day note: Not at BUILT. Six days does not stand in for the missing implementation.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-SALE-03 — Buyer Mode / Controlled Export

- What it is: Exposes only approved company-specific diligence data and Ask context; hides crown jewels and cross-company intelligence.
- Why it matters: This can follow the first commissioning. It is not the kernel and not the first daily loop.
- Current state: SYSTEM SPECIFIED (0.05). Domain D-SALE — Sale Readiness. Priority P2. Effort L.
- Exact remaining work: Buyer mode implementation
- Work classes: cursor_build, local_deterministic, human_commissioning.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Locatable implementation for BUILT. PROVEN still needs deterministic tests and material red-team or review evidence.
- Six-day note: Not at BUILT. Six days does not stand in for the missing implementation.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-SALE-04 — Buyer Attack & Transition Readiness

- What it is: Buyer Attack Audit + transition readiness; Wolf licence post-sale boundary preserved.
- Why it matters: This can follow the first commissioning. It is not the kernel and not the first daily loop.
- Current state: SYSTEM SPECIFIED (0.05). Domain D-SALE — Sale Readiness. Priority P2. Effort L.
- Exact remaining work: Attack audit + transition pack
- Work classes: cursor_build, local_deterministic, human_commissioning.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Locatable implementation for BUILT. PROVEN still needs deterministic tests and material red-team or review evidence.
- Six-day note: Not at BUILT. Six days does not stand in for the missing implementation.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

### CAP-STRAT-01 — 12-Week Year Cadence

- What it is: Vision→annual→12WY→department→individual; activity≠outcome.
- Why it matters: This can follow the first commissioning. It is not the kernel and not the first daily loop.
- Current state: SYSTEM BUILT (0.25). Domain D-STRAT — Strategy / Command. Priority P2. Effort M.
- Exact remaining work: Deterministic CAP prove
- Work classes: local_deterministic, human_commissioning.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- Evidence required to close: Deterministic verification plus material red-team or review evidence. BUILT is not PROVEN. A rendered desk is not that review.
- Six-day note: A local prove can be attempted. PROVEN still needs the review the scoring rules require. This pack does not supply that review.
- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.
- Deployed proof: DEPLOYED-ROUTE-PROOF-20260927 result is FAIL. No real Cloudflare Access JWT was presented to Beta :8788. Seated-role HTTP 200 landings and cross-role denials under a verified person were not observed. The local verifier suite is not that proof. That file is not a per-capability pass.

# Six-day critical path

SYSTEM = 19.65 / 77 = 25.52% ; STAFF READY = 0 ; HUMAN COMMISSIONED = 0 ; OPERATING ADOPTION = NOT MEASURED

Order is dependency order under rule W3-P5-PRIORITY-v1: the sign-in boundary, environment separation, Access posture, the rest of the control kernel, then the owner picture, then each business loop after the connector it names. Maturity state does not reorder this list.

This path does not promise that every step reaches READY in six days. The note on each step says what those six days can and cannot close. Nothing here moves money, writes a bank, or marks a human commissioning.

Production `:8787` is out of this path. Beta `:8788` is the boundary for any deployed-route prove.

### 1. CAP-CORE-02 — Person & Auth Identity

- Priority P0. SYSTEM READY. Effort none. Group: commission.
- Next bar: None for technical READY; adoption separate
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- In six days: Commissioning only. Not a build. A sign-in does not raise SYSTEM.

### 2. CAP-INTG-07 — Secrets & Environment Separation

- Priority P0. SYSTEM SPECIFIED. Effort L. Group: finish.
- Next bar: Matt names the vault product. Search on 27 Sep 2026 found no vault. Ledger stays SPECIFIED.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- In six days: BLOCKED_OWNER. Cursor does not build a second vault. A sign-in does not close this row.

### 3. CAP-MSC-02 — Access & Cloudflare Posture

- Priority P0. SYSTEM BUILT. Effort M. Group: finish.
- Next bar: Review note that is not this queue. The deny prove is recorded in commit 025dd13. Ledger stays BUILT.
- Dependency: CAP-CORE-02 is READY_FOR_HUMAN. That does not supply the review.
- Responsible role: Owner.
- In six days: Deny cases exit 0. PROVEN still needs the review. This pack does not supply it. Do not call Grok. Seated allow was not observed.

### 4. CAP-CORE-01 — Organisation Registry

- Priority P0. SYSTEM PROVEN. Effort S. Group: finish.
- Next bar: Seated allow and deny under a real Cloudflare session. The unsigned deny is recorded in commit 99f5a27. Ledger stays PROVEN.
- Dependency: CAP-CORE-02 is READY_FOR_HUMAN. That session was not observed.
- Responsible role: Owner.
- In six days: Unsigned, spoofed, and bad-JWT callers are 403 on the eight organisation reads. There is no separate org UI page. A seated allow was not observed. A development-subject 200 is not that proof.

### 5. CAP-CORE-03 — Role / Position / Assignment

- Priority P0. SYSTEM PROVEN. Effort S. Group: finish.
- Next bar: Seated read of the Haikal assignment list. The unsigned deny is commit 5a814fe. Ledger stays PROVEN.
- Dependency: The queue lists CAP-CORE-01 and CAP-CORE-02. The seated org read was not observed. This slice does not use it.
- Responsible role: Owner.
- In six days: Unsigned, spoofed, and bad-JWT callers are 403 on the assignment board. Commit 5a814fe. ASG-HAIKAL-CD-1 stays ACTIVE. ASG-HAIKAL-VE-1 stays ENDED. A seated allow was not observed. Do not add a grant. Ledger stays PROVEN.

### 6. CAP-CORE-04 — Permission & Authority Engine

- Priority P0. SYSTEM PROVEN. Effort S. Group: finish.
- Next bar: Seated allow and deny on the four seat routes. The unsigned catalog deny is commit c49237f. Ledger stays PROVEN.
- Dependency: The queue lists CAP-CORE-03. That seated assignment read was not observed. This slice does not use it. The critical path records no extra prerequisite.
- Responsible role: Owner.
- In six days: Unsigned, spoofed, and bad-JWT callers are 403 on GET /api/core/permissions and on /content-2.0, /bzg/uma-blu, /wolf, and /ggv/finance. Commit c49237f. No grant was added. A seated allow was not observed. Do not authorize by display name. Ledger stays PROVEN.

### 7. CAP-CORE-05 — Authority Limits Evaluator

- Priority P0. SYSTEM PROVEN. Effort S. Group: finish.
- Next bar: P0 queue CLOSED in commit fcae665. Empty-table deny recorded. Live count stayed 0. Ledger stays PROVEN.
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- In six days: The empty-table deny exits 0. Live org_authority_limits stayed 0. Unsigned callers are 403 on Beta :8788 pid 64196. A seated check was not observed. Ledger stays PROVEN. Do not insert a limit. Do not read 0 as a tolerance.

### 8. CAP-CORE-06 — Work Items / Promises / Decisions

- Priority P0. SYSTEM PROVEN. Effort S. Group: finish.
- Next bar: Seated read of the live work-item list. The temporary trail is commit 2229b21. Live core_work_items stayed 0.
- Dependency: CAP-CORE-02 is READY_FOR_HUMAN. That session was not observed.
- Responsible role: Owner.
- In six days: One item on a deleted catalog copy walked OPEN, IN_PROGRESS, BLOCKED, IN_PROGRESS, COMPLETED, VERIFIED. Unsigned Beta stays 403. A seated read was not observed. Ledger stays PROVEN. Do not create a live work item for the prove.

### 9. CAP-CORE-07 — Approval Engine

- Priority P0. SYSTEM PROVEN. Effort S. Group: finish.
- Next bar: Seated GET /api/core/approvals. The copy read is commit ab4af72. Live core_approval_requests stayed 0. A wide production policy pack was not authored.
- Dependency: The queue lists CAP-CORE-06. That seated read was not observed. This slice does not use the work-item trail.
- Responsible role: Owner.
- In six days: The copy read lists zero requests for PERS-MATT and inserts no policy. Commit ab4af72. Unsigned callers are 403 on Beta :8788 pid 64196. A seated read was not observed. Ledger stays PROVEN. Do not insert a pack. Do not treat GPO-HABITAT-CONTENT-PUBLISH or the six stored decisions as that pack.

### 10. CAP-CORE-08 — Segregation of Duties

- Priority P0. SYSTEM PROVEN. Effort S. Group: finish.
- Next bar: P0 queue BLOCKED_OWNER in commit e2cab4f. Self-close deny recorded. Live core_sod_constraints stayed 0. A finance pack exists only if Matt authors it. Ledger stays PROVEN.
- Dependency: The queue lists CAP-CORE-04 and CAP-CORE-07. Those seated reads were not observed. This slice does not use them. The critical path records no extra prerequisite.
- Responsible role: Owner.
- In six days: The submitter of a resolved close cannot verify it. Commit e2cab4f. Live core_sod_constraints stayed 0. Unsigned callers are 403 on Beta :8788 pid 64196. A seated check was not observed. Ledger stays PROVEN. Do not insert a finance pack. Do not read 0 as a finance rule.

### 11. CAP-CORE-09 — Evidence Requirements

- Priority P0. SYSTEM PROVEN. Effort S. Group: finish.
- Next bar: Live core_evidence_records is 4, not 3. The gate list is commit 9d0b83c. Six actions stay not gated. No requirement was inserted. Ledger stays PROVEN.
- Dependency: The queue lists CAP-CORE-07. That seated read was not observed. This list does not use it.
- Responsible role: Owner.
- In six days: The list names gated and not-gated actions. Commit 9d0b83c. test_work_loop.py left EVD-50e827bd invalidated. The count is 4. The no-delete trigger was not dropped. Do not mark CLOSED from that count. Ledger stays PROVEN.

### 12. CAP-CORE-10 — Exception / Override Governance

- Priority P0. SYSTEM PROVEN. Effort S. Group: finish.
- Next bar: Seated read of the three stored exceptions. The Owner Command list is commit b0fa859. Live core_governance_exceptions is 3, not 2. Cadence is not done.
- Dependency: The queue lists CAP-CORE-09. That evidence-count gap was not used. The critical path records no extra prerequisite.
- Responsible role: Owner.
- In six days: Owner Command lists the three REJECTED rows. Commit b0fa859. Unsigned callers are 403 on Beta :8788 pid 78725. A seated read was not observed. Ledger stays PROVEN. Do not insert a fourth row. Do not mark the cadence done.

### 13. CAP-STRAT-02 — Owner Radar / Mission Control

- Priority P1. SYSTEM BUILT. Effort M. Group: finish.
- Next bar: CAP-bound Model C prove; Progress is not this CAP alone
- Dependency: Requires CAP-CORE-01, CAP-CORE-06, CAP-CORE-07.
- Responsible role: Owner.
- In six days: A local prove can be attempted. PROVEN still needs the review the scoring rules require. This pack does not supply that review.

### 14. CAP-INTG-01 — Yanolja Connector

- Priority P1. SYSTEM ABSENT. Effort XL. Group: external.
- Next bar: Connector code/tests/contract
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- In six days: The outside system has no Wolf connector at BUILT. Do not invent its feed.

### 15. CAP-AMG-01 — Hotel PMS Orchestration

- Priority P1. SYSTEM SPECIFIED. Effort L. Group: finish.
- Next bar: Yanolja connector + orchestration code/tests
- Dependency: Requires CAP-INTG-01.
- Responsible role: ROLE-AMG-GM.
- In six days: Not at BUILT. Six days does not stand in for the missing implementation.

### 16. CAP-AMG-04 — Daily Hotel Operating State

- Priority P1. SYSTEM SPECIFIED. Effort L. Group: finish.
- Next bar: Machine-generated daily ops
- Dependency: Requires CAP-INTG-01, CAP-AMG-01.
- Responsible role: ROLE-AMG-GM.
- In six days: Not at BUILT. Six days does not stand in for the missing implementation.

### 17. CAP-INTG-02 — ESB Connector

- Priority P1. SYSTEM BUILT. Effort M. Group: finish.
- Next bar: Full ESB connector CAP + contract tests
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- In six days: A local prove can be attempted. PROVEN still needs the review the scoring rules require. This pack does not supply that review.

### 18. CAP-BZG-01 — F&B POS Orchestration

- Priority P1. SYSTEM BUILT. Effort M. Group: finish.
- Next bar: Full POS orchestration + ESB connector maturity
- Dependency: Requires CAP-INTG-02.
- Responsible role: ROLE-BZG-FB-OPS-LEAD.
- In six days: A local prove can be attempted. PROVEN still needs the review the scoring rules require. This pack does not supply that review.

### 19. CAP-BZG-03 — Venue Daily Close

- Priority P1. SYSTEM READY. Effort none. Group: commission.
- Next bar: Other venues are ADOPTION not SYSTEM
- Dependency: Requires CAP-INTG-02, CAP-BZG-01.
- Responsible role: ROLE-BZG-CLOSER.
- In six days: Commissioning only. Not a build. A sign-in does not raise SYSTEM.

### 20. CAP-INTG-04 — Bank Statement Connector

- Priority P1. SYSTEM BUILT. Effort M. Group: finish.
- Next bar: CAP-bound connector tests
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- In six days: A local prove can be attempted. PROVEN still needs the review the scoring rules require. This pack does not supply that review.

### 21. CAP-FIN-02 — Bank Statement Ingest & Reconcile

- Priority P1. SYSTEM BUILT. Effort M. Group: finish.
- Next bar: CAP-bound tests + connector honesty prove
- Dependency: Requires CAP-INTG-04.
- Responsible role: Owner.
- In six days: A local prove can be attempted. PROVEN still needs the review the scoring rules require. This pack does not supply that review.

### 22. CAP-FIN-01 — Wolf Accounting Core

- Priority P1. SYSTEM BUILT. Effort M. Group: finish.
- Next bar: Deterministic Core tests + red-team as Model C CAP
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- In six days: A local prove can be attempted. PROVEN still needs the review the scoring rules require. This pack does not supply that review.

### 23. CAP-FIN-03 — Entity Finance Boards

- Priority P1. SYSTEM BUILT. Effort M. Group: finish.
- Next bar: Shared CAP prove matrix all entities
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- In six days: A local prove can be attempted. PROVEN still needs the review the scoring rules require. This pack does not supply that review.

### 24. CAP-FIN-05 — Management Reporting

- Priority P1. SYSTEM SPECIFIED. Effort L. Group: finish.
- Next bar: Full P&L/BS/CF management pack
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- In six days: Not at BUILT. Six days does not stand in for the missing implementation.

### 25. CAP-GGV-02 — Publish Gate & Operator Loop

- Priority P1. SYSTEM READY. Effort none. Group: commission.
- Next bar: Human commissioning is ADOPTION; Metricool write still off
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: ROLE-GGV-CREATIVE-DIRECTOR.
- In six days: Commissioning only. Not a build. A sign-in does not raise SYSTEM.

### 26. CAP-GGV-01 — Content Machine

- Priority P1. SYSTEM BUILT. Effort M. Group: finish.
- Next bar: Full strategy-plan-asset-workflow-learn as one governed machine + tests
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: ROLE-GGV-CREATIVE-DIRECTOR.
- In six days: A local prove can be attempted. PROVEN still needs the review the scoring rules require. This pack does not supply that review.

### 27. CAP-GGV-04 — Lead Triage & Speed-to-Lead

- Priority P1. SYSTEM BUILT. Effort M. Group: finish.
- Next bar: Governed speed-to-lead capability with tests/red-team
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- In six days: A local prove can be attempted. PROVEN still needs the review the scoring rules require. This pack does not supply that review.

### 28. CAP-CRM-01 — Lead CRM

- Priority P1. SYSTEM BUILT. Effort M. Group: finish.
- Next bar: CAP-bound tests/red-team
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- In six days: A local prove can be attempted. PROVEN still needs the review the scoring rules require. This pack does not supply that review.

### 29. CAP-HR-01 — People Master Record

- Priority P1. SYSTEM BUILT. Effort M. Group: finish.
- Next bar: Canonical People Master per legal entity with CAP-bound tests
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- In six days: A local prove can be attempted. PROVEN still needs the review the scoring rules require. This pack does not supply that review.

### 30. CAP-HR-04 — Payroll Inputs

- Priority P1. SYSTEM SPECIFIED. Effort L. Group: finish.
- Next bar: Clean payroll-inputs CAP prove
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- In six days: Not at BUILT. Six days does not stand in for the missing implementation.

### 31. CAP-CORE-11 — SOP Factory

- Priority P1. SYSTEM SPECIFIED. Effort L. Group: finish.
- Next bar: Build SOP loop evidence-learn-approve-version-train-use
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- In six days: Not at BUILT. Six days does not stand in for the missing implementation.

### 32. CAP-CORE-12 — Delegation & Escalation Burn-down

- Priority P1. SYSTEM BUILT. Effort M. Group: finish.
- Next bar: Escalation burn-down + 7/30/90/365 independence tests
- Dependency: No extra prerequisite is recorded. The control kernel (CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY.
- Responsible role: Owner.
- In six days: A local prove can be attempted. PROVEN still needs the review the scoring rules require. This pack does not supply that review.

## Not on this path

P2 and P3 stay in the follow-after list. They are not blockers for the first operating loop. Sale capabilities are P2 because sale readiness is a named factor and can follow commissioning. Brand social performance, service-improvement capture, review capture, and the buyer room surfaces are P3.

# MODEL C SYSTEM EVIDENCE LEDGER

**Date:** 2026-09-17
**Class:** READ-ONLY evidence baseline. SIMULATION % not approved.
**Canon:** `docs/MODEL-C-CAPABILITY-CATALOG.md` + `docs/MODEL-C-SYSTEM-SCORING-RULES.md`
**PARTIAL CREDIT:** NOT AVAILABLE (no approved LRC packs) — whole-capability conservative maturity.
**OLD TRACKER SHORTCUT USED:** NO
**HUMAN ADOPTION COUNTED IN SYSTEM:** NO
**CURRENT HEALTH:** separate column

| CAP-ID | Domain | Name | Own | Maturity | Strongest evidence | Missing for next | Health | Conf | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CAP-CORE-01 | D-CORE | Organisation Registry | OWN | PROVEN | scripts/core/organisation.py + test_org_registry.py + docs/canon/ORG-REGISTRY-TRANSITIONAL.md | Deployed-route / live org UI prove for READY | UNKNOWN | HIGH | Org registry implemented+tested; transitional canon |
| CAP-CORE-02 | D-CORE | Person & Auth Identity | OWN | READY | f829f0c real auth JWT binding; test_real_auth_binding.py; test_person_auth_identity.py; scripts/core/identity.py cf_access.py; Beta :8788 200 | None for technical READY; adoption separate | HEALTHY | HIGH | CF JWT to Person on Beta; READY is not staff commissioning |
| CAP-CORE-03 | D-CORE | Role / Position / Assignment | OWN | PROVEN | test_role_position_assignment.py + ROLE-POSITION-ASSIGNMENT-TRANSITIONAL.md | Runtime board prove for READY | UNKNOWN | HIGH | Role/position/assignment tests green |
| CAP-CORE-04 | D-CORE | Permission & Authority Engine | OWN | PROVEN | scripts/core/rbac.py + test_rbac_permissions.py + test_phase2_5a_permissions.py + RBAC canon | Full seat-matrix deployed prove not re-run this audit | UNKNOWN | HIGH | Server RBAC exists+tested; conservative PROVEN |
| CAP-CORE-05 | D-CORE | Authority Limits Evaluator | OWN | PROVEN | f7d1874 authority limits; test_authority_limits.py; AUTHORITY-LIMITS canon | Broader runtime prove for READY; live limits at 0 is config | UNKNOWN | HIGH | Evaluator built+tested; limit values are not maturity |
| CAP-CORE-06 | D-CORE | Work Items / Promises / Decisions | OWN | PROVEN | 7114b95 work items; test_core_work_items.py; WORK-ITEMS.md; audit spine | End-to-end operator trail across all domains for READY | UNKNOWN | HIGH | Work item primitive + tests |
| CAP-CORE-07 | D-CORE | Approval Engine | OWN | PROVEN | dd039b2 approval engine + dual c054ac3 + policy 09d1c07; tests; Grok PASS after APR-RT-001 | Wide production policy packs | UNKNOWN | HIGH | Approval+dual+policy proven; Dual is requirement class |
| CAP-CORE-08 | D-CORE | Segregation of Duties | OWN | PROVEN | aa4ec07 SoD; test_sod_constraints.py; SEGREGATION-OF-DUTIES.md; Grok PASS | Broader finance SoD live packs for READY | UNKNOWN | HIGH | PARTIAL CREDIT NOT AVAILABLE |
| CAP-CORE-09 | D-CORE | Evidence Requirements | OWN | PROVEN | 1f71765 evidence requirements; test_evidence_requirements.py; EVIDENCE-REQUIREMENTS.md; Grok PASS | Universal evidence packs on all material actions for READY | UNKNOWN | HIGH | PARTIAL CREDIT NOT AVAILABLE |
| CAP-CORE-10 | D-CORE | Exception / Override Governance | OWN | PROVEN | b83d1d6 exception override; test_exception_override.py; EXCEPTION-OVERRIDE.md; Grok PASS | Operating exception review cadence for READY | UNKNOWN | HIGH | PARTIAL CREDIT NOT AVAILABLE |
| CAP-CORE-11 | D-CORE | SOP Factory | OWN | SPECIFIED | Master Spec + catalog SOP Factory full-loop intent; no complete SOP Factory implementation in scripts/core | Build SOP loop evidence-learn-approve-version-train-use | UNKNOWN | MED | Catalog/Spec only — not BUILT |
| CAP-CORE-12 | D-CORE | Delegation & Escalation Burn-down | OWN | BUILT | 8c4285a delegation + test_delegation.py + DELEGATION.md + DLG-RT-001 fix; Grok re-review PASS | Escalation burn-down + 7/30/90/365 independence tests | UNKNOWN | HIGH | Delegation module strong; full CAP intent incomplete so BUILT |
| CAP-GGV-01 | D-GGV | Content Machine | OWN | BUILT | Content boards/scripts/skills (Metricool, smart upload, phase2 content) exist | Full strategy-plan-asset-workflow-learn as one governed machine + tests | UNKNOWN | MED | Partial content stack |
| CAP-GGV-02 | D-GGV | Publish Gate & Operator Loop | OWN | READY | f833f37 publish gate + 3f9a838 operator UI; tests; HABITAT-PUBLISH-GATE.md; Grok reviews; Beta serve 200 | Human commissioning is ADOPTION; Metricool write still off | HEALTHY | HIGH | SYSTEM READY; human loop not SYSTEM; write-lock does not auto-block READY |
| CAP-GGV-03 | D-GGV | Client Profitability | OWN | SPECIFIED | Catalog + GGV margin targets; no Client P&L machinery found | Build client/contract P&L allocation | UNKNOWN | MED | PARTIAL CREDIT NOT AVAILABLE |
| CAP-GGV-04 | D-GGV | Lead Triage & Speed-to-Lead | OWN | BUILT | Lead boards/ingest patterns (Habitat leads, Ivy stale) — partial triage | Governed speed-to-lead capability with tests/red-team | UNKNOWN | MED | Leads UI/ingest is not full CAP PROVEN |
| CAP-GGV-05 | D-GGV | Brand Social Performance | DERIVE | BUILT | metricool_read_client.py; sync_metricool_*; analyze_metricool_performance; test_metricool_isolation.py | Governed DERIVE views + PROVEN red-team | UNKNOWN | MED | DERIVE/read path partial; Metricool existence is not mature |
| CAP-GGV-06 | D-GGV | Intercompany Client Mode | OWN | SPECIFIED | Catalog + Matt IN SCOPE near-term decision; explicit non-build this mission | Intercompany client mode implementation | UNKNOWN | HIGH | Specified in canon; not built |
| CAP-AMG-01 | D-AMG | Hotel PMS Orchestration | OWN | SPECIFIED | Catalog OWN+INTEGRATE boundary; Master Spec hotel OS; no Wolf Yanolja connector implementation found | Yanolja connector + orchestration code/tests | UNKNOWN | HIGH | Yanolja product existence is not Wolf maturity |
| CAP-AMG-02 | D-AMG | Guest Journey Operations | OWN | SPECIFIED | Catalog guest journey intent; discovery docs only | Journey workflow implementation | UNKNOWN | MED | PARTIAL CREDIT NOT AVAILABLE |
| CAP-AMG-03 | D-AMG | Packages as Products | OWN | SPECIFIED | Catalog packages-as-products | Package product machinery | UNKNOWN | MED | PARTIAL CREDIT NOT AVAILABLE |
| CAP-AMG-04 | D-AMG | Daily Hotel Operating State | OWN | SPECIFIED | Catalog daily hotel operating state | Machine-generated daily ops | UNKNOWN | MED | PARTIAL CREDIT NOT AVAILABLE |
| CAP-AMG-05 | D-AMG | Hotel Revenue & Yield | OWN | SPECIFIED | Catalog hotel revenue and yield | Yield machinery | UNKNOWN | MED | PARTIAL CREDIT NOT AVAILABLE |
| CAP-AMG-06 | D-AMG | Guest Experience Loop | OWN | SPECIFIED | Catalog guest experience loop | SLA/incident trail | UNKNOWN | MED | PARTIAL CREDIT NOT AVAILABLE |
| CAP-AMG-07 | D-AMG | Service Improvement Loop | OWN | SPECIFIED | Catalog service improvement loop | Review-to-improve loop | UNKNOWN | MED | PARTIAL CREDIT NOT AVAILABLE |
| CAP-BZG-01 | D-BZG | F&B POS Orchestration | OWN | BUILT | esb_close_snapshot.py used by Uma close; F&B POS orchestration partial via ESB facts | Full POS orchestration + ESB connector maturity | UNKNOWN | MED | Snapshot is not full orchestration CAP |
| CAP-BZG-02 | D-BZG | Venue P&L & Management Rollup | OWN | SPECIFIED | Catalog venue P&L + rollup | Venue P&L dashboards as capability | UNKNOWN | MED | PARTIAL CREDIT NOT AVAILABLE |
| CAP-BZG-03 | D-BZG | Venue Daily Close | OWN | READY | 909954d Uma Blu daily close; venue_close.py; esb_close_snapshot.py; test_uma_blu_daily_close.py; UMA-BLU-DAILY-CLOSE.md; Grok review PASS | Other venues are ADOPTION not SYSTEM | HEALTHY | HIGH | Shared CAP READY; Uma adoption separate |
| CAP-BZG-04 | D-BZG | Inventory & Stock Control | OWN | SPECIFIED | Catalog inventory and stock; ESB SoT noted | Variance/waste analysis machinery | UNKNOWN | MED | PARTIAL CREDIT NOT AVAILABLE |
| CAP-BZG-05 | D-BZG | Central Kitchen & Shared Cost Allocation | OWN | SPECIFIED | Catalog central kitchen allocation | Allocation engine | UNKNOWN | MED | PARTIAL CREDIT NOT AVAILABLE |
| CAP-BZG-06 | D-BZG | Recipe / Cost Standards | OWN | SPECIFIED | Catalog recipe/cost standards | BOM/yield machinery | UNKNOWN | MED | PARTIAL CREDIT NOT AVAILABLE |
| CAP-BZG-07 | D-BZG | Review & Reputation Capture | OBSERVE | SPECIFIED | Catalog OBSERVE reviews | Observe/ingest path | UNKNOWN | LOW | PARTIAL CREDIT NOT AVAILABLE |
| CAP-HR-01 | D-HR | People Master Record | OWN | BUILT | HR desk/people records patterns; org/person core overlaps | Canonical People Master per legal entity with CAP-bound tests | UNKNOWN | MED | Partial HR surfaces |
| CAP-HR-02 | D-HR | Hiring & Onboarding | OWN | SPECIFIED | Catalog hiring/onboarding | Workflows | UNKNOWN | MED | PARTIAL CREDIT NOT AVAILABLE |
| CAP-HR-03 | D-HR | Training & Competency | OWN | SPECIFIED | Catalog training/competency; SOP Factory link | Training ack machinery | UNKNOWN | MED | PARTIAL CREDIT NOT AVAILABLE |
| CAP-HR-04 | D-HR | Payroll Inputs | OWN | SPECIFIED | Catalog payroll inputs; atrium payroll banners exist as UI fragments | Clean payroll-inputs CAP prove | UNKNOWN | MED | UI fragments are not CAP PROVEN |
| CAP-HR-05 | D-HR | Retention & Succession Signals | OWN | SPECIFIED | Catalog retention/succession | Signals machinery | UNKNOWN | MED | PARTIAL CREDIT NOT AVAILABLE |
| CAP-FIN-01 | D-FIN | Wolf Accounting Core | OWN | BUILT | Accounting core scripts/boards (atrium-finance, journals, CoA config missions) | Deterministic Core tests + red-team as Model C CAP | UNKNOWN | MED | Substantial finance UI/API; conservative BUILT |
| CAP-FIN-02 | D-FIN | Bank Statement Ingest & Reconcile | INTEGRATE | BUILT | Bank statement ingest/reconcile path; Aug statements ingested historically | CAP-bound tests + connector honesty prove | UNKNOWN | MED | INTEGRATE workflow partial |
| CAP-FIN-03 | D-FIN | Entity Finance Boards | OWN | BUILT | Entity finance boards (GGV/Atrium/Uma surfaces) on Beta stack | Shared CAP prove matrix all entities | UNKNOWN | MED | PARTIAL CREDIT NOT AVAILABLE |
| CAP-FIN-04 | D-FIN | Invoicing & Receivables | OWN | BUILT | Invoicing Save-Issue paths (Amanda Habitat invoices) | CAP-bound tests/red-team; Amanda human prove is ADOPTION | UNKNOWN | MED | PARTIAL CREDIT NOT AVAILABLE |
| CAP-FIN-05 | D-FIN | Management Reporting | OWN | SPECIFIED | Catalog management reporting; Reports sections exist partially | Full P&L/BS/CF management pack | UNKNOWN | MED | PARTIAL CREDIT NOT AVAILABLE |
| CAP-FIN-06 | D-FIN | Intercompany Billing | OWN | SPECIFIED | Catalog intercompany billing paired with GGV-06 | Implementation | UNKNOWN | HIGH | PARTIAL CREDIT NOT AVAILABLE |
| CAP-FIN-07 | D-FIN | Budget / Forecast / Cash Cadence | OWN | SPECIFIED | Catalog budget/forecast/cash | 13-week cash machinery | UNKNOWN | MED | PARTIAL CREDIT NOT AVAILABLE |
| CAP-FIN-08 | D-FIN | Profit Leakage Intelligence | OWN | SPECIFIED | Catalog profit leakage intelligence | Leakage engine | UNKNOWN | MED | PARTIAL CREDIT NOT AVAILABLE |
| CAP-PROC-01 | D-PROC | Supplier Register & Intelligence | OWN | SPECIFIED | Catalog supplier register | Implementation | UNKNOWN | MED | PARTIAL CREDIT NOT AVAILABLE |
| CAP-PROC-02 | D-PROC | Purchase & Approval Flow | OWN | SPECIFIED | Catalog purchase and approval flow | PO-match-pay with SoD | UNKNOWN | MED | PARTIAL CREDIT NOT AVAILABLE |
| CAP-PROC-03 | D-PROC | Payment Tracking | OWN | SPECIFIED | Catalog payment tracking; Alchemist payment tracking known gap | Payment runs + settlement evidence | UNKNOWN | MED | PARTIAL CREDIT NOT AVAILABLE |
| CAP-CRM-01 | D-CRM | Lead CRM | OWN | BUILT | Lead CRM boards (Habitat/Atrium leads) | CAP-bound tests/red-team | UNKNOWN | MED | PARTIAL CREDIT NOT AVAILABLE |
| CAP-CRM-02 | D-CRM | Customer Identity & Memory | OWN | SPECIFIED | Catalog customer identity/memory | Identity graph | UNKNOWN | MED | PARTIAL CREDIT NOT AVAILABLE |
| CAP-CRM-03 | D-CRM | Package Intelligence | OWN | SPECIFIED | Catalog package intelligence | Implementation | UNKNOWN | MED | PARTIAL CREDIT NOT AVAILABLE |
| CAP-CRM-04 | D-CRM | Email Marketing Wire | INTEGRATE | BUILT | Klaviyo/AC wiring distinctions in rules; Numbers tiles | Honest connector prove | UNKNOWN | MED | INTEGRATE partial |
| CAP-MSC-01 | D-MSC | Asset & Maintenance Register | OWN | SPECIFIED | Catalog asset/maintenance | Register | UNKNOWN | MED | PARTIAL CREDIT NOT AVAILABLE |
| CAP-MSC-02 | D-MSC | Access & Cloudflare Posture | OWN | BUILT | Cloudflare Access posture managed; Cipher sweeps; Matt-owned flips preserved | CAP-bound automated posture prove as READY | UNKNOWN | MED | Operational CF practice; not Model C PROVEN pack |
| CAP-MSC-03 | D-MSC | Compliance Pack | OWN | SPECIFIED | Catalog compliance pack | Licence/statutory evidence pack | UNKNOWN | MED | PARTIAL CREDIT NOT AVAILABLE |
| CAP-MSC-04 | D-MSC | Cybersecurity Baseline | OWN | SPECIFIED | Catalog cybersecurity baseline | MFA/device posture CAP | UNKNOWN | MED | PARTIAL CREDIT NOT AVAILABLE |
| CAP-MSC-05 | D-MSC | Documents / Records / Legal Defensibility | OWN | SPECIFIED | Catalog documents/records/legal; legal files dashboards exist partially | Callable records + legal hold CAP | UNKNOWN | MED | PARTIAL CREDIT NOT AVAILABLE |
| CAP-STRAT-01 | D-STRAT | 12-Week Year Cadence | OWN | BUILT | 12WY/Radar/Helm cadence surfaces | Deterministic CAP prove | UNKNOWN | MED | PARTIAL CREDIT NOT AVAILABLE |
| CAP-STRAT-02 | D-STRAT | Owner Radar / Mission Control | OWN | BUILT | radar.html / Owner Radar / Progress cockpit adjacent | CAP-bound Model C prove; Progress is not this CAP alone | UNKNOWN | MED | Do not inflate via Progress Dashboard |
| CAP-INTEL-01 | D-INTEL | Orchestration / Reasoning Surface | OWN | SPECIFIED | Catalog orchestration surface; agent army exists but not one institutional WI | One WI experience implementation | UNKNOWN | MED | Helpers are not CAP READY |
| CAP-INTEL-02 | D-INTEL | Authorised Retrieval & Institutional Memory | OWN | SPECIFIED | RULE-Authorised-Knowledge-Resolution-2026-09-17.md + Habitat knowledge sweep delivery | Runtime authorised retrieval prove | UNKNOWN | HIGH | Canon/rule is not READY |
| CAP-INTEL-03 | D-INTEL | Provenance / Confidence / Conflict Resolution | OWN | SPECIFIED | Same knowledge-resolution principle (provenance/confidence/conflict) | Runtime conflict resolution machinery | UNKNOWN | HIGH | Docs are not READY |
| CAP-INTEL-04 | D-INTEL | Decision Memory | OWN | SPECIFIED | Catalog decision memory; work items/approvals leave trails but not full Decision Memory CAP | Recallable decision memory product | UNKNOWN | MED | PARTIAL CREDIT NOT AVAILABLE |
| CAP-INTEL-05 | D-INTEL | Learning / Experiments / Performance Policy | OWN | SPECIFIED | Catalog learning/experiments policy | Approve-to-rule learning loop | UNKNOWN | MED | PARTIAL CREDIT NOT AVAILABLE |
| CAP-INTG-01 | D-INTG | Yanolja Connector | INTEGRATE | ABSENT | Catalog INTEGRATE Yanolja; search found no Wolf Yanolja connector implementation | Connector code/tests/contract | UNKNOWN | HIGH | Vendor is not Wolf; ABSENT after search |
| CAP-INTG-02 | D-INTG | ESB Connector | INTEGRATE | BUILT | esb_close_snapshot.py + Uma close integration of ESB facts | Full ESB connector CAP + contract tests | UNKNOWN | MED | Close snapshot is not complete ESB connector |
| CAP-INTG-03 | D-INTG | Google Workspace Connector | INTEGRATE | BUILT | Gmail/Drive/Calendar connectors used operationally across Wolf | CAP-bound INTEGRATE prove pack | UNKNOWN | MED | PARTIAL CREDIT NOT AVAILABLE |
| CAP-INTG-04 | D-INTG | Bank Statement Connector | INTEGRATE | BUILT | Bank statement file import path (ingest registry) | CAP-bound connector tests | UNKNOWN | MED | PARTIAL CREDIT NOT AVAILABLE |
| CAP-INTG-05 | D-INTG | Metricool Connector | INTEGRATE | BUILT | metricool_read_client + sync + isolation tests; write fail-closed | PROVEN red-team of connector contract | UNKNOWN | HIGH | Read path built; write-lock OK if boundary honest |
| CAP-INTG-06 | D-INTG | Technology & Capability Registries | OWN | SPECIFIED | Catalog technology and capability registries | Tech inventory + exit conditions product | UNKNOWN | MED | PARTIAL CREDIT NOT AVAILABLE |
| CAP-INTG-07 | D-INTG | Secrets & Environment Separation | OWN | SPECIFIED | Catalog secrets/env separation; .env.example + Beta/Prod sacred rules | Secrets management CAP prove | UNKNOWN | MED | Keep SPECIFIED without secrets vault prove |
| CAP-DR-01 | D-DR | Backup / Restore Testing / Disaster Recovery | OWN | SPECIFIED | Catalog backup/restore; B2/NAS practices; Phoenix DR agent exists | Restore-tested CAP evidence | UNKNOWN | MED | Practice is not PROVEN restore tests |
| CAP-DR-02 | D-DR | Crown Jewel Protection | OWN | SPECIFIED | Catalog crown jewel protection; Matt-only playbook default in Spec | Independent failure domains prove | UNKNOWN | MED | PARTIAL CREDIT NOT AVAILABLE |
| CAP-SALE-01 | D-SALE | Continuous Sale Evidence Pack | OWN | SPECIFIED | Catalog Continuous Sale Evidence Pack; 60 cells are controls not caps | Evidence pack automation consuming domains | UNKNOWN | HIGH | Controls must not inflate SYSTEM |
| CAP-SALE-02 | D-SALE | Buyer Data Room | OWN | SPECIFIED | Catalog Buyer Data Room; Vault helper exists historically | Continuously updated VDR product | UNKNOWN | MED | PARTIAL CREDIT NOT AVAILABLE |
| CAP-SALE-03 | D-SALE | Buyer Mode / Controlled Export | OWN | SPECIFIED | Catalog Buyer Mode / Controlled Export | Buyer mode implementation | UNKNOWN | MED | PARTIAL CREDIT NOT AVAILABLE |
| CAP-SALE-04 | D-SALE | Buyer Attack & Transition Readiness | OWN | SPECIFIED | Catalog Buyer Attack and Transition | Attack audit + transition pack | UNKNOWN | MED | PARTIAL CREDIT NOT AVAILABLE |

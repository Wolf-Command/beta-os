# CURSOR STDIN PROMPT — BZG-P2P-PR-1
# Purchase Request vertical slice (FIRST in armed ship queue)
# Paste entire file to cursor-agent stdin. Do not print process args.

Written: 2026-10-04 ~16:53 WITA (box arm artifact). Launch ONLY on Studio when control path is up.
Workspace: `/Users/wolfterminal/beta-os`
Launch form (operator only — never print argv here):
  `/Users/wolfterminal/.local/bin/cursor-agent -p --force --model composer-2.5 --workspace /Users/wolfterminal/beta-os`
  NO `--trust`. stdin = this prompt. `start_new_session`. One Cursor at a time. Leave private worker pid 63443 alone.
Branch: local Beta only. No push. No prod `:8787`. No wolf-system clone onto the box.

Pack: `BZG-P2P-PR-1`
Parent pack: `BZG-PROCURE-TO-PAY-1` / God Mode GM-024 (DESIGNED — do not mark implemented from this slice alone)
Target states: BUILT → DEPLOYED BETA → ENGINEERING PROVED → READY FOR HUMAN TEST
`staff_ready` stays **false** until a human. Do not set `human_commissioned` true. Do not call PASS / READY / ENG_PROVED from an index or from Peaches.

---

## Mission (one vertical slice only)

On Beta only, implement a canonical **Purchase Request** record and UI/API path that a real authenticated person can create and save, with:

1. **Real authenticated person** (identity from existing org auth — not a hardcoded name)
2. **Real ACTIVE assignment** that grants the PR create permission under person → assignment → role → entity/outlet scope → permission
3. **Real outlet REQUIRED** on every PR (permanent field). Legal entity ENT-BZG plus one of the configured outlets:
   - Uma Blu
   - Blu Zone Rainforest Restaurant & Bar
   - Pool Bar
   - Merah Underground
   - Rooftop Bar
   - Room Service
   - Catering
   Outlets are **config**, not new app code per outlet. Do not invent a new outlet table if config already exists — reuse BZG outlet/brand/location config already in Beta.
4. Request **lines** with item, qty, unit
5. **Reason** / purpose
6. **Requester** (bound to authenticated person + assignment)
7. **Timestamp** (created_at / submitted_at as appropriate)
8. **Status** (at least draft → submitted; keep approval handoff honest)
9. **Save** that persists to Beta catalog (or the Beta P2P store already used by BZG ops — do not invent a second SoR)
10. **Audit** trail for create/update/status change
11. **My Work / approval handoff** where the existing My Work / approval machinery applies — wire into it; do not invent a parallel inbox

Optional read-only provenance: pointer to an existing Alchemist `pr_orders.id` when linking historical context. Pointer only. Do **not** seed fake operational rows. Do **not** invent purchases.

---

## Real masters (read / link — do not fabricate)

Where available on Studio, use real supplier/item master data:

- Alchemist SoR (Studio mount of alchemist DB, or documented Beta projection). Box RO snapshot counts (for orientation only, not for inventing rows): `pr_orders` 200, `pr_order_lines` 674, `suppliers` 80, `pr_vendors` 31, `pr_vendor_items` 495, `locations` 1 (Uma Blu). Snapshot path on box was `/workspace/alchemist-live-ro.db` — **do not copy that file into Beta live catalog with shutil.copy2**.
- Beta org persons, assignments, scopes, permissions already in `catalog/content_library.sqlite`.
- Do **not** invent supplier names, prices, or PR lines to fill a dashboard.
- Do **not** create Almond Milk as a recipe (irrelevant to this pack; leave Recipe Builder alone).

---

## Scope fence (STOP if asked to expand)

IN SCOPE:
- PR object + required outlet + lines + reason + requester + timestamps + status + save + audit
- Permission gate via assignment (not hardcoded Hariyanto / Devi / Zayen / Amanda / Matt / Iza)
- My Work / approval handoff if existing machinery can accept a PR approval item
- Temp/schema-only sqlite tests
- Local Beta migration if needed (idempotent)
- RESULT stamp under `state/reliability/`

OUT OF SCOPE (do not build in this Cursor run):
- PO, consolidated PO, receiving, nota extraction, AP, READY TO PAY, payment, bank recon, GL
- Seeding sample POs or fake operational purchases
- Prod mutation, push, PR #1 merge
- Rewriting Daily Close `VDC-470e741f` or `VDC-87202768`
- Changing God Mode denominator (43)
- Finance Mark Paid / money movement
- Rainforest/Pool Bar menu archaeology

---

## Hard locks

- Beta only. Prod sacred (read-only). Never mutate prod.
- Do not mutate protected close `VDC-470e741f-d889-437a-9a40-1ec9c083fb95`.
- Do not mutate close `VDC-87202768`.
- Tests on **temp / schema-only sqlite**. NEVER `shutil.copy2` live `catalog/content_library.sqlite` into a test path that then gets written as if it were live content.
- No invent operational transactions.
- Authority model: PERSON → ASSIGNMENT → ROLE → ENTITY/OUTLET SCOPE → PERMISSION → AUTHORITY LIMIT. Separation of duties. Nobody approves their own PR where policy prohibits it.
- Do not hardcode person names into workflow logic. Status values like stored Alchemist `Awaiting Devi` must not become code branches keyed on the string "Devi".
- `staff_ready=false`. Do not claim HUMAN COMMISSIONED.
- One Cursor. Leave pid 63443 alone. No dual agent.
- No `--trust`. No printing of process args in logs you write.
- Local commit only if your standing Beta rule requires it for this pack; Owner arm says **no_commit** while control path was down — prefer no commit unless an existing Beta build rule on Studio explicitly requires a local commit for this class of change. If unsure: implement + migrate + test + RESULT; leave commit decision to operator. Never push.

---

## Implementation guidance (prefer reuse)

1. Read first (live Beta tree):
   - Existing BZG Uma / procure / ops modules under `scripts/core/` (search `bzg_ops`, `purchase`, `pr_`, `uma_ops`)
   - `scripts/serve_beta.py` routes for `/bzg/*`
   - Org RBAC helpers (assignments, scopes, permissions)
   - My Work / approval request tables and APIs if present
   - Outlet/brand config for the seven outlets
2. Add the smallest migration that creates/ensures PR tables or columns with: entity_id, outlet (required), department optional, requester_person_id, requester_assignment_id, status, reason, timestamps, optional `alchemist_pr_order_id` provenance, line table (item ref or free text only if master missing — prefer master), qty, unit, audit events.
3. API: authenticated create/save/get/list scoped by assignment. Reject missing outlet. Reject unauthenticated. Reject wrong entity scope.
4. UI: a real Beta page or existing desk surface where a scoped person creates a PR. Not a shell tile that says "coming soon".
5. My Work: if `core_approval_requests` / My Work pipeline exists, enqueue approval on submit; else document in RESULT that handoff is NOT WIRED and leave a clear TODO — do not fake an approval inbox.
6. Tests: new focused test file under `scripts/tests/`. Use temp sqlite. Cover: outlet required, auth required, assignment gate, save+audit, no hardcoded person names, deny without scope. Keep unrelated Beta tests green if you touch shared modules.

---

## Prove (engineering)

When done, on Beta:

- Migration applied (idempotent re-run safe)
- Tests green (record pass/fail counts)
- Unsigned / unauthenticated PR write denied
- Authenticated subject with real assignment can create PR with required outlet and at least one line
- Missing outlet → validation error (not silent default to Uma)
- Audit row exists for create
- `staff_ready` remains false
- Protected closes untouched
- No live Alchemist write
- No invent seeded purchases

---

## STOP conditions (exit non-zero / write STOP result)

STOP and write RESULT with status STOPPED if any of:

1. Studio tree is not `/Users/wolfterminal/beta-os` or prod paths are being edited
2. Required outlet config for the seven outlets is missing and would require inventing outlets
3. No real person+assignment exists that can own a PR without hardcoding a name into code (report which seats exist; do not invent PERS/ASG rows unless a prior Owner-approved migration pattern for this pack explicitly allows seeding **roles/permissions only**)
4. Implementing PR would require mutating `VDC-470e741f` or copying live catalog with `shutil.copy2`
5. Scope creep into PO/receiving/payment is demanded by broken dependencies — record blocker instead of expanding
6. Another Cursor / pid 63443 conflict — do not fight; STOP
7. Tests cannot run without cloning live content_library into a writable test DB via shutil.copy2

---

## Result file (required)

Write BOTH:

- `state/reliability/BZG-P2P-PR-1-RESULT-2026-10-04.md`
- `state/reliability/BZG-P2P-PR-1-RESULT-2026-10-04.json`

JSON fields (minimum):

```json
{
  "pack_id": "BZG-P2P-PR-1",
  "finished_at_wita": "...",
  "status": "IMPLEMENTATION_DONE_LOCAL_PASS | STOPPED | FAILED",
  "eng_proved": false,
  "staff_ready": false,
  "human_commissioned": false,
  "ready_for_human_test": false,
  "deployed_beta": false,
  "tests_pass": 0,
  "tests_fail": 0,
  "migration_id": null,
  "routes": [],
  "protected_close_untouched": true,
  "no_prod": true,
  "no_shutil_copy2_live_catalog": true,
  "stop_reason": null
}
```

Set `ready_for_human_test` true ONLY if: real route exists, permission via assignment works, tests pass, page is not a shell, and a human can attempt one real PR on Beta without invented data. Still keep `staff_ready=false`.

Set `deployed_beta` true ONLY if Beta serve path actually reloaded/serves the new code on `:8788` (or the Studio Beta port in standing use). Do not claim Cloudflare Access signed-in proof.

---

## Exit

`EXIT:0` when implementation done (or honest STOP), tests recorded, RESULT written.
`EXIT:1` on failed tests or unsafe condition without RESULT.

Do not call this pack PASS. Do not raise God Mode. Do not change denominator 43.

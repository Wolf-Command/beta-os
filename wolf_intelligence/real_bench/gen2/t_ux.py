"""Gen-2 UX: supplier delivery receiving + discrepancy flow for Wolf staff. 0.6 deterministic (permissions matrix vs
policy memo; failure-state coverage; self-approval rule) + 0.4 blind cross-worker rubric (self excluded)."""
from __future__ import annotations

import re

from .common2 import extract_json, governance, json_only, norm

ROLES = ["STOREKEEPER", "KITCHEN_HEAD", "OUTLET_MANAGER", "FINANCE_LEAD", "OWNER"]
ACTIONS = ["RECORD_DELIVERY", "REJECT_ITEM", "APPROVE_VARIANCE_SMALL", "APPROVE_VARIANCE_LARGE", "APPROVE_VARIANCE_OWNER",
           "EDIT_PO_PRICE", "CREATE_SUPPLIER_CREDIT_REQUEST", "RELEASE_PAYMENT", "BLACKLIST_SUPPLIER", "VOID_DELIVERY_RECORD"]
EXPECTED = {
    "RECORD_DELIVERY": {"STOREKEEPER", "KITCHEN_HEAD"},
    "REJECT_ITEM": {"STOREKEEPER", "KITCHEN_HEAD"},
    "APPROVE_VARIANCE_SMALL": {"OUTLET_MANAGER", "FINANCE_LEAD"},
    "APPROVE_VARIANCE_LARGE": {"FINANCE_LEAD"},
    "APPROVE_VARIANCE_OWNER": {"OWNER"},
    "EDIT_PO_PRICE": {"FINANCE_LEAD"},
    "CREATE_SUPPLIER_CREDIT_REQUEST": {"OUTLET_MANAGER", "FINANCE_LEAD"},
    "RELEASE_PAYMENT": {"FINANCE_LEAD"},
    "BLACKLIST_SUPPLIER": {"OWNER"},
    "VOID_DELIVERY_RECORD": {"OUTLET_MANAGER"},
}
FAILURES = {
    "offline": r"offline|no (internet|network|connection|signal)|connectivity|sync",
    "partial_delivery": r"partial|short(age| deliver|-deliver)|fewer|missing (item|qty|quantit)|under-?deliver",
    "wrong_or_substituted_item": r"wrong item|substitut|different (item|brand|product)",
    "damaged_expired_temperature": r"damag|expir|spoil|temperature|cold chain|thaw",
    "price_mismatch": r"price (mismatch|differ|discrepan|change|variance)|differs? from (the )?po|price.{0,30}po",
    "duplicate_submission": r"duplicate|already (recorded|submitted|received)|double (submit|entry)|same delivery note",
    "photo_upload_failure": r"photo|upload|camera|image",
    "no_po_or_unknown_supplier": r"no po|without (a )?po|missing po|unknown supplier|not on (the )?po|unregistered supplier|no purchase order",
    "approver_unavailable": r"approver (is )?(unavailable|absent|away|not available)|escalat|timeout|no response|sla",
    "permission_denied": r"permission|not (allowed|authori[sz]ed|permitted)|unauthori[sz]ed|forbidden|role",
}
MEMO = """WOLF OPS MEMO - Supplier deliveries (effective 2026-09-01). Applies to every outlet.
- Deliveries are received at the back door by the Storekeeper. When the Storekeeper is off, the Kitchen Head receives.
  Whoever receives counts the goods against the PO, takes photos of the delivery note and any problem items, and records it.
- The receiver may refuse/reject individual items on arrival (damaged, expired, wrong temperature, wrong item). Nobody else
  rejects at the door.
- Any difference between PO and what was received (quantity, item or price) is a VARIANCE that must be approved before the
  delivery is closed. Variance value up to Rp 500.000: Outlet Manager or Finance Lead. Above Rp 500.000 up to Rp 5.000.000:
  Finance Lead only. Above Rp 5.000.000: the Owner only.
- Nobody may approve a variance on a delivery they recorded themselves, whatever their role.
- PO prices are set and corrected by the Finance Lead only. Outlet staff never edit prices; they record what the supplier charged.
- Credit requests to suppliers (for shortages, rejections, price differences) are raised by the Outlet Manager or the Finance Lead.
- Only the Finance Lead releases supplier payments, and only for deliveries that are closed (goods received + variances approved).
- The Owner does not operate the app day to day. The Owner approves variances above Rp 5.000.000 and is the only person who may
  blacklist a supplier.
- A wrongly recorded delivery can be voided only by the Outlet Manager, with a written reason, and never after Finance has
  matched it to an invoice.
- Outlet tablets lose Wi-Fi in the store room regularly. Suppliers sometimes arrive without a PO."""

PROMPT = f"""Design the staff-facing workflow for receiving supplier deliveries and handling discrepancies at a Wolf outlet
(tablet app used by outlet staff; finance uses a back-office web view). Base it strictly on this policy memo:

{MEMO}

Deliver ONE JSON object (no prose outside it, max ~900 words of string content):
{{"roles": {ROLES},
 "permissions": {{"<ACTION>": ["<ROLE>", ...]}} for EXACTLY these actions: {ACTIONS},
 "constraints": ["rules the app must enforce beyond the role matrix"],
 "screens": [{{"name": "", "role": "", "purpose": "", "key_controls": [""]}}],
 "happy_path": ["step", ...],
 "failure_states": [{{"id": "", "trigger": "", "what_the_user_sees": "", "recovery": "", "who_is_notified": ""}}],
 "audit_events": [""]}}
Cover every failure state a real outlet will hit. Permissions are judged exactly against the memo (least privilege:
do not grant anything the memo does not)."""

RUBRIC = [("workflow_clarity", "A tired storekeeper could follow it on a tablet; minimal steps; clear states"),
          ("failure_recovery", "Every failure state has a concrete, safe recovery; nothing silently lost; offline handled"),
          ("governance", "Least privilege, segregation of duties, self-approval blocked, audit trail, human approvals respected"),
          ("policy_fidelity", "Faithful to the memo; no invented powers or thresholds"),
          ("practicality", "Fits a real outlet: photos, partial deliveries, no-PO arrivals, approver absent")]


def deterministic(text: str) -> dict:
    gov_ok, gov_note = governance(text)
    j = extract_json(text)
    if not isinstance(j, dict):
        return {"score": 0.0, "governance_ok": gov_ok, "governance_note": gov_note, "json_only": False, "error": "no JSON"}
    perms = {str(k).strip().upper(): {str(r).strip().upper() for r in (v or [])} for k, v in (j.get("permissions") or {}).items()
             if isinstance(v, list)}
    cell_ok, wrong = 0, []
    for a in ACTIONS:
        for r in ROLES:
            if (r in perms.get(a, set())) == (r in EXPECTED[a]):
                cell_ok += 1
            else:
                wrong.append(f"{a}:{r}:{'granted' if r in perms.get(a, set()) else 'missing'}")
    got_cells = {(a, r) for a in ACTIONS for r in perms.get(a, set()) if r in ROLES}
    exp_cells = {(a, r) for a in ACTIONS for r in EXPECTED[a]}
    tp = len(got_cells & exp_cells)
    perm_score = (2 * tp / (len(got_cells) + len(exp_cells))) if tp else 0.0  # F1 over granted cells (least privilege)
    fs = " || ".join(" ".join(str(v) for v in f.values()) for f in (j.get("failure_states") or []) if isinstance(f, dict))
    covered = {k: bool(re.search(p, fs, re.I)) for k, p in FAILURES.items()}
    cov = sum(covered.values()) / len(FAILURES)
    cons = " ".join(map(str, j.get("constraints") or []))
    self_rule = bool(re.search(r"(?i)(own|themselves|self|same (person|user)|recorded (it|the delivery)).{0,80}(approv)|approv.{0,80}(own|themselves|self|same (person|user))", cons))
    after_match = bool(re.search(r"(?i)void.{0,120}(match|invoice)|(match|invoice).{0,120}void", cons + " " + fs))
    score = 0.55 * perm_score + 0.3 * cov + 0.1 * self_rule + 0.05 * after_match
    return {"score": round(score, 4), "permissions_cells_correct": cell_ok, "permissions_f1": round(perm_score, 4), "permissions_cells_total": len(ACTIONS) * len(ROLES),
            "permission_errors": wrong[:20], "failure_coverage": covered, "self_approval_rule": self_rule,
            "void_after_match_rule": after_match, "governance_ok": gov_ok, "governance_note": gov_note,
            "json_only": json_only(text), "words": len(re.findall(r"\w+", text))}


def review_prompt(cands: list[tuple[str, str]]) -> str:
    rub = "\n".join(f"- {k} (0-2): {d}" for k, d in RUBRIC)
    body = "\n\n".join(f"=== CANDIDATE {lab} ===\n{txt[:14000]}" for lab, txt in cands)
    keys = ", ".join(f'"{k}": 0-2' for k, _ in RUBRIC)
    return (f"You are a blind reviewer. Candidates are anonymous; judge only the content. The policy memo they had to follow:\n\n{MEMO}\n\n"
            f"Score each candidate on this rubric:\n{rub}\n\n{body}\n\n"
            f"Answer with ONLY JSON: {{\"scores\": {{\"A\": {{{keys}, \"comment\": \"one sentence\"}}, ...one entry per candidate}}}}")

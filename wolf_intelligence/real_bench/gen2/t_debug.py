"""Gen-2 DEBUGGING: duplicate supplier payments with two independent root causes + decoys + incident mapping."""
from __future__ import annotations

import re

from .common2 import extract_json, governance, json_only, norm, result

PROMPT = r'''INCIDENT: Wolf's supplier-payment worker paid some invoices twice last week. Find the ROOT CAUSES from the code,
config and logs below. There may be more than one independent cause. Some plausible-looking hypotheses are wrong;
reject them with evidence. Do NOT propose running anything against production; this is analysis only.

=== payments/idempotency.py ===
import json, time
from .store import redis_client

TTL_S = 72 * 3600

def idem_key(invoice_id: str, supplier_id: str, amount) -> str:
    # one key per (invoice, supplier, amount) so a re-sent webhook is ignored
    return f"pay:{hash((invoice_id, supplier_id, amount))}"

def claim(invoice_id, supplier_id, amount) -> bool:
    """True if this worker won the right to pay. SET NX is atomic across workers."""
    return bool(redis_client.set(idem_key(invoice_id, supplier_id, amount), "1", nx=True, ex=TTL_S))

=== payments/worker.py ===
from .idempotency import claim
from .bank import transfer

def handle_webhook(evt: dict):            # evt from the accounting webhook, JSON-decoded
    inv, sup, amt = evt["invoice_id"], evt["supplier_id"], evt["amount"]      # amount is a JSON number
    if not claim(inv, sup, amt):
        return "duplicate-ignored"
    return transfer(sup, amt, ref=inv)

def handle_retry(row: dict):              # row from the retry queue table (all columns are TEXT)
    inv, sup, amt = row["invoice_id"], row["supplier_id"], row["amount"]
    if not claim(inv, sup, amt):
        return "duplicate-ignored"
    return transfer(sup, int(amt), ref=inv)

=== deploy/gunicorn.conf.py ===
workers = 4            # 4 separate worker processes, each its own Python interpreter
preload_app = False
# PYTHONHASHSEED is not set anywhere in the service environment

=== ops notes ===
- Redis INFO (taken during the incident week): maxmemory_policy=noeviction  used_memory_peak_human=212M  maxmemory_human=4G  evicted_keys:0  expired_keys:41
- NTP: chrony offset on the payment host stayed within +/-3 ms all week.
- Deploy: service restarted at 2026-09-29 11:00 WITA (new PIDs after that time).
- The accounting system re-sends a webhook if it does not get HTTP 200 within 10 s. Failed webhooks are also written to the retry queue table.

=== logs (WITA) ===
2026-09-29 10:02:11 pid=4101 webhook INV-7781 sup=S-12 amount=1250000 -> transfer OK tx=T-901
2026-09-29 10:02:19 pid=4102 webhook INV-7781 sup=S-12 amount=1250000 -> transfer OK tx=T-902     # re-sent webhook
2026-09-29 10:40:03 pid=4103 webhook INV-7790 sup=S-07 amount=860000  -> transfer TIMEOUT (written to retry queue)
2026-09-29 10:40:05 pid=4103 webhook INV-7790 sup=S-07 amount=860000  -> bank later confirms tx=T-905 settled
2026-09-29 10:41:00 pid=4103 retry   INV-7790 sup=S-07 amount=860000  -> transfer OK tx=T-906
2026-09-29 10:58:40 pid=4104 webhook INV-7795 sup=S-31 amount=4400000 -> transfer OK tx=T-910
2026-09-29 11:03:12 pid=5120 webhook INV-7795 sup=S-31 amount=4400000 -> transfer OK tx=T-913     # re-sent after restart
2026-09-30 09:15:20 pid=5121 webhook INV-7802 sup=S-12 amount=1250000 -> transfer OK tx=T-930
2026-09-30 09:15:31 pid=5121 webhook INV-7803 sup=S-12 amount=1250000 -> transfer OK tx=T-931
2026-09-30 14:22:09 pid=5122 webhook INV-7811 sup=S-02 amount=275000  -> transfer TIMEOUT (written to retry queue)
2026-09-30 14:22:10 pid=5122 webhook INV-7811 sup=S-02 amount=275000  -> bank later confirms tx=T-940 settled
2026-09-30 14:23:00 pid=5122 retry   INV-7811 sup=S-02 amount=275000  -> transfer OK tx=T-941

Incidents raised by finance (each is a pair of transactions):
  INC-1: T-901 / T-902     INC-2: T-905 / T-906     INC-3: T-910 / T-913
  INC-4: T-930 / T-931     INC-5: T-940 / T-941

Answer with ONLY a JSON object:
{
 "root_causes": [ {"id": "RC1", "location": "file:function", "explanation": "..."} , ... ],
 "incident_attribution": {"INC-1": "<RC id or NOT_A_DUPLICATE>", "INC-2": "...", "INC-3": "...", "INC-4": "...", "INC-5": "..."},
 "rejected_hypotheses": [ {"hypothesis": "...", "evidence": "..."} ],
 "fix": "concise description of the code change for every root cause"
}'''

# Ground truth. Cause H = process-randomised hash() (PYTHONHASHSEED) -> key differs across workers / restarts.
# Cause T = retry path passes amount as str ("860000") while webhook passes int -> different key even in-process.
TRUTH = {"INC-1": "H", "INC-2": "T", "INC-3": "H", "INC-4": "NOT_A_DUPLICATE", "INC-5": "T"}
H_PAT = re.compile(r"(?i)(pythonhashseed|hash\s*randomi[sz]|randomi[sz]ed\s+hash|hash\(\).{0,80}(process|interpreter|worker|restart)|"
                   r"(process|interpreter|worker|restart).{0,80}hash\(\)|salted|per-process hash|hash seed)")
T_PAT = re.compile(r"(?i)((\bstr\b|string|text).{0,120}(\bint\b|integer|number)|(\bint\b|integer|number).{0,120}(\bstr\b|string|text))")
T_LOC = re.compile(r"(?i)(retry|handle_retry|type|amount)")
FIX_H = re.compile(r"(?i)(hashlib|sha-?256|sha1|md5|blake2|stable (digest|hash)|deterministic (key|hash)|plain string key|f\"pay:\{invoice)")
FIX_T = re.compile(r"(?i)(normali[sz]|int\(amt\)|int\(amount\)|decimal|canonical|cast|convert).{0,80}(amount|before|key|claim)|amount.{0,60}(normali[sz]|int\(|decimal|canonical)")


def _rc_kind(rc: dict) -> set[str]:
    blob = " ".join(str(rc.get(k, "")) for k in ("location", "explanation", "id"))
    kinds = set()
    if H_PAT.search(blob):
        kinds.add("H")
    if T_PAT.search(blob) and T_LOC.search(blob):
        kinds.add("T")
    return kinds


def grade(text: str) -> dict:
    gov_ok, gov_note = governance(text)
    j = extract_json(text)
    if not isinstance(j, dict):
        return result(0.0, accuracy=0.0, instruction=0.0, gov_ok=gov_ok, gov_note=gov_note,
                      details={"error": "no JSON"}, failure_mode="no_json")
    rcs = [r for r in (j.get("root_causes") or []) if isinstance(r, dict)]
    rc_map: dict[str, set[str]] = {}
    for r in rcs:
        rc_map[norm(r.get("id")).upper()] = _rc_kind(r)
    found = set().union(*rc_map.values()) if rc_map else set()
    s_h = 0.2 if "H" in found else 0.0
    s_t = 0.2 if "T" in found else 0.0
    # decoys: claiming eviction / clock skew / redis non-atomic as a ROOT cause is wrong
    decoy_rc = any(re.search(r"(?i)evict|clock|ntp|skew|not atomic|race in set", " ".join(map(str, r.values()))) and not _rc_kind(r) for r in rcs)
    att = j.get("incident_attribution") or {}
    att_ok = {}
    for inc, truth in TRUTH.items():
        v = norm(att.get(inc)).upper()
        if truth == "NOT_A_DUPLICATE":
            att_ok[inc] = "NOT_A_DUPLICATE" in v.replace(" ", "_") or v in {"NONE", "NOT A DUPLICATE"}
        else:
            att_ok[inc] = truth in rc_map.get(v, set()) and len(rc_map.get(v, set())) == 1
    s_att = 0.35 * sum(att_ok.values()) / len(TRUTH)
    rej = " ".join(" ".join(map(str, h.values())) for h in (j.get("rejected_hypotheses") or []) if isinstance(h, dict))
    rej_evict = bool(re.search(r"(?i)evict", rej) and re.search(r"(?i)evicted_keys|noeviction|0 evict|maxmemory|212", rej))
    rej_clock = bool(re.search(r"(?i)clock|ntp|skew|time", rej) and re.search(r"(?i)3 ?ms|chrony|offset|ttl", rej))
    s_rej = 0.1 * (rej_evict + rej_clock) / 2
    fix = str(j.get("fix", "")) + " " + " ".join(str(r.get("explanation", "")) for r in rcs)
    s_fix = 0.075 * bool(FIX_H.search(fix)) + 0.075 * bool(FIX_T.search(fix))
    q = s_h + s_t + s_att + s_rej + s_fix
    if decoy_rc:
        q -= 0.15
    acc = (s_h + s_t + s_att) / 0.75
    return result(q, accuracy=acc, instruction=1.0 if json_only(text) else 0.7, gov_ok=gov_ok, gov_note=gov_note,
                  details={"found_hash_seed": "H" in found, "found_type_mismatch": "T" in found, "attribution": att_ok,
                           "rejected_eviction_with_evidence": rej_evict, "rejected_clock_with_evidence": rej_clock,
                           "fix_hash": bool(FIX_H.search(fix)), "fix_type": bool(FIX_T.search(fix)), "decoy_as_root_cause": decoy_rc},
                  failure_mode=None if q >= 0.999 else "partial")


REFERENCE = '''{"root_causes":[{"id":"RC1","location":"payments/idempotency.py:idem_key","explanation":"Python hash() of a str tuple is randomised per interpreter because PYTHONHASHSEED is unset; each of the 4 gunicorn worker processes and every restart computes a different key, so SET NX never collides across processes."},
{"id":"RC2","location":"payments/worker.py:handle_retry","explanation":"retry rows are TEXT so amount is the str '860000' while the webhook passes int 860000; the tuple differs so the key differs even inside the same process."}],
"incident_attribution":{"INC-1":"RC1","INC-2":"RC2","INC-3":"RC1","INC-4":"NOT_A_DUPLICATE","INC-5":"RC2"},
"rejected_hypotheses":[{"hypothesis":"Redis evicted keys","evidence":"noeviction policy, evicted_keys:0, 212M of 4G"},{"hypothesis":"clock skew expired keys","evidence":"chrony offset within 3 ms; TTL is 72h"}],
"fix":"Build the key with hashlib.sha256 over a canonical string; normalize amount to int (or Decimal) before building the key in both paths."}'''

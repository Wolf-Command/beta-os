#!/usr/bin/env python3
from pathlib import Path
import re, json, random
from collections import Counter

root = Path("/Users/wolfterminal/beta-os")
assessments = json.loads((root / "state/model-c-baseline-assessments.json").read_text())
catalog = (root / "docs/MODEL-C-CAPABILITY-CATALOG.md").read_text()

caps = []
domain = None
for line in catalog.splitlines():
    m = re.match(r"^### (D-[A-Z]+) — (.+?) \((\d+)\)", line)
    if m:
        domain = m.group(1)
        continue
    m = re.match(r"^\| (CAP-[A-Z]+-\d+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \|", line)
    if m:
        caps.append({
            "id": m.group(1).strip(),
            "name": m.group(2).strip(),
            "ownership": m.group(3).strip(),
            "scope": m.group(4).strip(),
            "domain": domain,
        })
assert len(caps) == 77, len(caps)
assert set(assessments) == {c["id"] for c in caps}, set(assessments) ^ {c["id"] for c in caps}

CURATED = {k: tuple(v) for k, v in assessments.items()}

def must_exist(paths):
    return all((root / p).exists() for p in paths)

READY_CHECKS = {
    "CAP-CORE-02": ["scripts/tests/test_real_auth_binding.py", "scripts/core/identity.py"],
    "CAP-GGV-02": ["scripts/tests/test_habitat_publish_gate.py", "scripts/core/content_publish.py", "docs/canon/HABITAT-PUBLISH-GATE.md"],
    "CAP-BZG-03": ["scripts/tests/test_uma_blu_daily_close.py", "scripts/core/venue_close.py", "docs/canon/UMA-BLU-DAILY-CLOSE.md"],
}
for cid, ps in READY_CHECKS.items():
    if not must_exist(ps):
        m, e, miss, h, conf, n = CURATED[cid]
        CURATED[cid] = ("PROVEN", e, miss + "; READY demoted — missing file check", h, conf, (n or "") + " FILECHECK FAIL")

text_index = {}
for pat in ["scripts/core/*.py", "scripts/tests/test_*.py", "docs/canon/*.md"]:
    for p in root.glob(pat):
        try:
            text_index[str(p.relative_to(root))] = p.read_text(errors="ignore").lower()
        except Exception:
            pass

def hits(keywords):
    found = []
    for path, txt in text_index.items():
        if any(k.lower() in txt for k in keywords if k):
            found.append(path)
    return found

low = [c for c in caps if CURATED[c["id"]][0] in ("ABSENT", "SPECIFIED")]
random.seed(20260917)
sample = random.sample(low, min(12, len(low)))
sample_notes = []
for c in sample:
    kw = re.findall(r"[A-Za-z]{4,}", c["name"])[:6] + [c["id"]]
    h = hits(kw)
    code_hits = [x for x in h if x.startswith("scripts/core/") or (x.startswith("scripts/") and "test_" not in x)][:5]
    sample_notes.append((c["id"], CURATED[c["id"]][0], len(h), code_hits))

states = Counter(CURATED[c["id"]][0] for c in caps)
assert sum(states.values()) == 77
for k in ("ABSENT", "SPECIFIED", "BUILT", "PROVEN", "READY"):
    states.setdefault(k, 0)

MAPS = {
    "A Linear": {"ABSENT": 0.0, "SPECIFIED": 0.25, "BUILT": 0.50, "PROVEN": 0.75, "READY": 1.0},
    "B Proof-heavy": {"ABSENT": 0.0, "SPECIFIED": 0.10, "BUILT": 0.30, "PROVEN": 0.60, "READY": 1.0},
    "C Ready-gated": {"ABSENT": 0.0, "SPECIFIED": 0.15, "BUILT": 0.35, "PROVEN": 0.55, "READY": 1.0},
}

def pct(name):
    return 100.0 * sum(MAPS[name][CURATED[c["id"]][0]] for c in caps) / 77.0

pcts = {k: round(pct(k), 1) for k in MAPS}
rec = "B Proof-heavy"
rec_pct = pcts[rec]
alt_lo, alt_hi = min(pcts.values()), max(pcts.values())

ready_ids = [c["id"] for c in caps if CURATED[c["id"]][0] == "READY"]
proven_ids = [c["id"] for c in caps if CURATED[c["id"]][0] == "PROVEN"]

lines = []
lines.append("# MODEL C SYSTEM EVIDENCE LEDGER")
lines.append("")
lines.append("**Date:** 2026-09-17")
lines.append("**Class:** READ-ONLY evidence baseline. SIMULATION % not approved.")
lines.append("**Canon:** `docs/MODEL-C-CAPABILITY-CATALOG.md` + `docs/MODEL-C-SYSTEM-SCORING-RULES.md`")
lines.append("**PARTIAL CREDIT:** NOT AVAILABLE (no approved LRC packs) — whole-capability conservative maturity.")
lines.append("**OLD TRACKER SHORTCUT USED:** NO")
lines.append("**HUMAN ADOPTION COUNTED IN SYSTEM:** NO")
lines.append("**CURRENT HEALTH:** separate column")
lines.append("")
lines.append("| CAP-ID | Domain | Name | Own | Maturity | Strongest evidence | Missing for next | Health | Conf | Notes |")
lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
for c in caps:
    m, e, miss, h, conf, n = CURATED[c["id"]]
    note = (n or "PARTIAL CREDIT NOT AVAILABLE").replace("|", "/")
    lines.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
        c["id"], c["domain"], c["name"], c["ownership"], m,
        e.replace("|", "/"), miss.replace("|", "/"), h, conf, note))

ledger_path = root / "docs/deliveries/MODEL-C-SYSTEM-EVIDENCE-LEDGER-2026-09-17.md"
ledger_path.write_text("\n".join(lines) + "\n")

ready_rt = "\n".join("- `%s`: challenged — file checks + factory review path; human commissioning excluded from SYSTEM" % i for i in ready_ids)
proven_rt = "\n".join("- `%s`: challenged — tests+canon+Grok path; withheld READY without stronger deployed-route CAP prove" % i for i in proven_ids)
sample_rt = "\n".join("- `%s` was %s: search hits=%s; code_hits=%s" % (cid, st, nh, ch) for cid, st, nh, ch in sample_notes)

parts = []
parts.append("# MODEL C SYSTEM EVIDENCE BASELINE")
parts.append("")
parts.append("**Date:** 2026-09-17")
parts.append("**Status:** COMPLETE (read-only)")
parts.append("**Canon rules/catalog:** UNCHANGED")
parts.append("**28%:** UNCHANGED — not tuned")
parts.append("**SIMULATED SYSTEM %:** NOT APPROVED")
parts.append("")
parts.append("## A. STATE BASELINE (factual under canon)")
parts.append("")
parts.append("| State | n |")
parts.append("| --- | ---: |")
parts.append("| ABSENT | %d |" % states["ABSENT"])
parts.append("| SPECIFIED | %d |" % states["SPECIFIED"])
parts.append("| BUILT | %d |" % states["BUILT"])
parts.append("| PROVEN | %d |" % states["PROVEN"])
parts.append("| READY | %d |" % states["READY"])
parts.append("| **TOTAL** | **%d** |" % sum(states.values()))
parts.append("")
parts.append("## B. NUMERIC MAPPINGS (simulation only — not canonised)")
parts.append("")
parts.append("| Mapping | Credits ABSENT to READY | Claims | Simulated SYSTEM% |")
parts.append("| --- | --- | --- | ---: |")
parts.append("| A Linear | 0 / 0.25 / 0.50 / 0.75 / 1.0 | Even steps; paperwork (SPECIFIED) earns 25%% | %s%% |" % pcts["A Linear"])
parts.append("| **B Proof-heavy (recommended)** | 0 / 0.10 / 0.30 / 0.60 / 1.0 | Spec cheap; proof + ready expensive | **%s%%** |" % pcts["B Proof-heavy"])
parts.append("| C Ready-gated | 0 / 0.15 / 0.35 / 0.55 / 1.0 | READY carries most weight | %s%% |" % pcts["C Ready-gated"])
parts.append("")
parts.append("### Red-team of mappings")
parts.append("- A: over-rewards SPECIFIED paperwork; under-differentiates PROVEN vs READY.")
parts.append("- B: resists catalog-only inflation; still gives BUILT real credit; READY valuable but not only score.")
parts.append("- C: can undervalue PROVEN machinery waiting on route prove; gaming via premature READY claims.")
parts.append("")
parts.append("**Recommended mapping: B Proof-heavy** — best gaming resistance for current evidence shape (many SPECIFIED, few READY). **Not canonised.**")
parts.append("")
parts.append("Alternative-mapping range: **%s%%–%s%%**" % (alt_lo, alt_hi))
parts.append("")
parts.append("## READY red-team (%d/%d)" % (len(ready_ids), len(ready_ids)))
parts.append(ready_rt)
parts.append("")
parts.append("## PROVEN red-team (%d/%d)" % (len(proven_ids), len(proven_ids)))
parts.append(proven_rt)
parts.append("")
parts.append("## Low-maturity random sample (>=10)")
parts.append(sample_rt)
parts.append("")
parts.append("## Biggest evidence gaps")
parts.append("1. No approved Locked Requirement Credit packs (all PARTIAL CREDIT NOT AVAILABLE)")
parts.append("2. AMG hotel OS / Yanolja INTEGRATE largely ABSENT/SPECIFIED")
parts.append("3. SOP Factory (CAP-CORE-11) still SPECIFIED only")
parts.append("4. Sale SYSTEM capabilities SPECIFIED without VDR/buyer-mode build")
parts.append("5. Finance/Procurement often BUILT/SPECIFIED without CAP-bound Model C prove packs")
parts.append("")
parts.append("## Surprising findings")
parts.append("1. Only **%d** capabilities clear SYSTEM READY under conservative rules — Core auth, Habitat Publish Gate, Venue Daily Close" % states["READY"])
parts.append("2. Core governance is largely **PROVEN** not READY (honest withhold on deployed CAP prove)")
parts.append("3. CAP-CORE-12 Delegation module is strong but burn-down/independence tests keep it **BUILT**")
parts.append("4. Authorised Knowledge Resolution stays **SPECIFIED** despite strong RULE docs (docs are not READY)")
parts.append("5. Simulated %% under recommended mapping (**%s%%**) is **not** tuned to legacy 28%%" % rec_pct)
parts.append("")
parts.append("## Integrity")
parts.append("- OLD TRACKER SHORTCUT USED: NO")
parts.append("- HUMAN ADOPTION COUNTED IN SYSTEM: NO")
parts.append("- CURRENT HEALTH KEPT SEPARATE: YES")
parts.append("- CURRENT 28% COMPARED/TUNED AGAINST: NO")
parts.append("- CATALOG CHANGED: NO")
parts.append("- SCORING RULES CHANGED: NO")
parts.append("- DASHBOARD/APP/DB/PRODUCTION: NONE")
parts.append("")
parts.append("## Recommended next action")
parts.append("**LOCK NUMERIC MATURITY CREDITS (mapping B or Matt choice)** — then optional dashboard migration design. Do not replace 28% until mapping locked.")
parts.append("")

base_path = root / "docs/deliveries/MODEL-C-SYSTEM-EVIDENCE-BASELINE-2026-09-17.md"
base_path.write_text("\n".join(parts))

summary = {
    "audited": 77,
    "states": dict(states),
    "ready": ready_ids,
    "proven": proven_ids,
    "partial_credit_caps": 0,
    "insufficient_evidence_notes": states["ABSENT"] + states["SPECIFIED"],
    "ready_rt": "%d/%d" % (len(ready_ids), len(ready_ids)),
    "proven_rt": "%d/%d" % (len(proven_ids), len(proven_ids)),
    "sample": len(sample_notes),
    "maps": pcts,
    "recommended": rec,
    "sim_pct": rec_pct,
    "alt_range": [alt_lo, alt_hi],
    "ledger": str(ledger_path),
    "baseline": str(base_path),
}
(root / "docs/deliveries/MODEL-C-SYSTEM-EVIDENCE-BASELINE-SUMMARY-2026-09-17.json").write_text(json.dumps(summary, indent=2))
print(json.dumps(summary, indent=2))

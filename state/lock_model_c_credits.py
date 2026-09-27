#!/usr/bin/env python3
from pathlib import Path
import re, json
from collections import Counter
from decimal import Decimal, ROUND_HALF_UP

root = Path("/Users/wolfterminal/beta-os")
ledger = (root / "docs/deliveries/MODEL-C-SYSTEM-EVIDENCE-LEDGER-2026-09-17.md").read_text()
catalog = (root / "docs/MODEL-C-CAPABILITY-CATALOG.md").read_text()
rules_path = root / "docs/MODEL-C-SYSTEM-SCORING-RULES.md"

CREDITS = {
    "ABSENT": Decimal("0.00"),
    "SPECIFIED": Decimal("0.05"),
    "BUILT": Decimal("0.25"),
    "PROVEN": Decimal("0.80"),
    "READY": Decimal("1.00"),
}
VERSION = "MODEL-C-SYSTEM-CREDITS-v1.0-2026-09-17"

cat_ids = []
for line in catalog.splitlines():
    m = re.match(r"^\| (CAP-[A-Z]+-\d+) \|", line)
    if m:
        cat_ids.append(m.group(1))
assert len(cat_ids) == 77, len(cat_ids)

ledger_map = {}
name_map = {}
for line in ledger.splitlines():
    if not line.startswith("| CAP-"):
        continue
    parts = [p.strip() for p in line.strip("|").split("|")]
    if len(parts) < 5:
        continue
    cid, name, maturity = parts[0], parts[2], parts[4]
    if not re.match(r"^CAP-[A-Z]+-\d+$", cid):
        continue
    if maturity not in CREDITS:
        raise SystemExit("BAD maturity %s for %s" % (maturity, cid))
    if cid in ledger_map:
        raise SystemExit("DUP %s" % cid)
    ledger_map[cid] = maturity
    name_map[cid] = name

if set(ledger_map) != set(cat_ids):
    raise SystemExit("SET MISMATCH %s" % (set(ledger_map) ^ set(cat_ids),))

counts = Counter(ledger_map.values())
for s in CREDITS:
    counts.setdefault(s, 0)
assert counts["ABSENT"] == 1 and counts["SPECIFIED"] == 45 and counts["BUILT"] == 19 and counts["PROVEN"] == 9 and counts["READY"] == 3
assert sum(counts.values()) == 77

total = sum(CREDITS[ledger_map[cid]] for cid in cat_ids)
exact = total / Decimal(77) * Decimal(100)
pct = exact.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)

UNDER = [
    "CAP-FIN-05", "CAP-HR-04", "CAP-INTEL-02", "CAP-INTEL-03",
    "CAP-INTG-07", "CAP-MSC-05", "CAP-DR-01",
]
GEN = sorted([cid for cid, m in ledger_map.items() if m in ("ABSENT", "SPECIFIED") and cid not in UNDER])
assert len(UNDER) == 7
assert len(GEN) == 39, len(GEN)

credits_canon = """# MODEL C — SYSTEM NUMERIC MATURITY CREDITS (CANONICAL)

**Status:** CANONICAL  
**Scoring model version:** `%s`  
**Approved:** Matt APPROVED — LOCK MODEL C NUMERIC MATURITY CREDITS (2026-09-17, chat)  
**Companion rules:** `docs/MODEL-C-SYSTEM-SCORING-RULES.md`  
**Denominator catalog:** `docs/MODEL-C-CAPABILITY-CATALOG.md` (77)  
**WHERE:** `docs/MODEL-C-SYSTEM-NUMERIC-CREDITS.md`

## Credits (constitutional)

| State | Credit |
| --- | ---: |
| ABSENT | 0.00 |
| SPECIFIED | 0.05 |
| BUILT | 0.25 |
| PROVEN | 0.80 |
| READY | 1.00 |

## Meaning

These credits represent **technical capability maturity** only.

They do **not** represent effort, time, cost, adoption, business value, founder independence, financial maturity, or sale readiness.

| State | Semantics |
| --- | --- |
| ABSENT = 0%% | No sufficient approved specification exists. |
| SPECIFIED = 5%% | Wolf knows what the correct machine should be; documentation alone earns only token SYSTEM maturity. |
| BUILT = 25%% | Locatable implementation exists, but until independently proven it remains substantially an implementation claim. |
| PROVEN = 80%% | Deterministic verification plus required review/red-team has retired most technical implementation risk. |
| READY = 100%% | Technical deployment/runtime/dependency proof is complete for the capability's intended boundary. READY is independent of human operating adoption. |

## Sanity checks (intentional)

If every canonical capability were only:

- SPECIFIED → SYSTEM = **5%%**
- BUILT → SYSTEM = **25%%**
- PROVEN → SYSTEM = **80%%**
- READY → SYSTEM = **100%%**

## Formula

Equal capability weighting. No domain weights. No hidden weights. No entity/venue adoption inside SYSTEM.

```
SYSTEM%% = SUM(canonical capability maturity credits) / 77 × 100
```

Locked Requirement Credit applies only where an approved versioned partial-credit pack exists.

## Governance

Future credit changes require explicit Matt approval.  
Never tune credits to improve displayed %%.  
Never silently rewrite historical scores when the model changes — keep versioned history.

## Version history

| Version | Date | Change |
| --- | --- | --- |
| `%s` | 2026-09-17 | Initial lock (mapping D / verification-weighted). Prior candidate B not adopted. |
""" % (VERSION, VERSION)
(root / "docs/MODEL-C-SYSTEM-NUMERIC-CREDITS.md").write_text(credits_canon)

rt = rules_path.read_text()
if "MODEL-C-SYSTEM-NUMERIC-CREDITS.md" not in rt:
    banner = """

---

## Numeric maturity credits (LOCKED %s)

Canonical credits: `docs/MODEL-C-SYSTEM-NUMERIC-CREDITS.md`

| State | Credit |
| --- | ---: |
| ABSENT | 0.00 |
| SPECIFIED | 0.05 |
| BUILT | 0.25 |
| PROVEN | 0.80 |
| READY | 1.00 |

`SYSTEM%% = SUM(credits) / 77 × 100` (equal weights; LRC only with approved pack).

Official SYSTEM baseline (docs, not dashboard): `docs/deliveries/MODEL-C-SYSTEM-BASELINE-OFFICIAL-2026-09-17.md`.  
Displayed Progress **28%%** remains legacy until separate dashboard migration approve.
""" % VERSION
    rules_path.write_text(rt.rstrip() + "\n" + banner + "\n")

baseline_official = """# MODEL C SYSTEM BASELINE — OFFICIAL (docs)

**Status:** OFFICIAL MODEL C SYSTEM BASELINE — **not on dashboard**  
**Scoring model version:** `%s`  
**Calculated:** 2026-09-17  
**Source ledger:** `docs/deliveries/MODEL-C-SYSTEM-EVIDENCE-LEDGER-2026-09-17.md`  
**WHERE:** `docs/deliveries/MODEL-C-SYSTEM-BASELINE-OFFICIAL-2026-09-17.md`

## Reconciliation

| Check | Result |
| --- | --- |
| Catalog CAP-IDs | 77 |
| Ledger CAP-IDs | 77 |
| Set equality | PASS |
| Counts ABSENT/SPECIFIED/BUILT/PROVEN/READY | 1 / 45 / 19 / 9 / 3 |
| Sum of credits | %s |
| SYSTEM%% = sum/77×100 | **%s%%** (exact %s) |
| BASELINE RECONCILIATION | **PASS** |

## Official baseline

**CALCULATED SYSTEM BASELINE: %s%%**  
**SYSTEM BASELINE STATUS: OFFICIAL**

Do **not** put on Progress Dashboard yet.  
Displayed **28%%** remains **LEGACY BUILD-TRACKER ESTIMATE — PENDING MODEL C SCORING MIGRATION**.  
Do not call 28%% SYSTEM progress.

## Formula used

Equal weights · credits v1.0 · no LRC packs applied · no domain weights.
""" % (VERSION, total, pct, exact, pct)
(root / "docs/deliveries/MODEL-C-SYSTEM-BASELINE-OFFICIAL-2026-09-17.md").write_text(baseline_official)

backlog = [
    "# MODEL C EVIDENCE REMEDIATION BACKLOG — POTENTIALLY UNDER-EVIDENCED",
    "",
    "**Date:** 2026-09-17",
    "**Class:** Bounded backlog. Do NOT change maturity without required CAP-bound evidence.",
    "**Do not interfere with Habitat or Uma commissioning.**",
    "**WHERE:** `docs/deliveries/MODEL-C-EVIDENCE-REMEDIATION-BACKLOG-2026-09-17.md`",
    "",
    "These seven are currently **SPECIFIED** in the official baseline but may be more mature if CAP-bound evidence is gathered (PROVE WHAT EXISTS, not automatically BUILD SOMETHING NEW).",
    "",
    "| CAP-ID | Name | Current maturity | Investigation intent |",
    "| --- | --- | --- | --- |",
]
for cid in UNDER:
    backlog.append("| %s | %s | SPECIFIED | Seek CAP-bound implementation/tests/runtime evidence before any maturity raise |" % (cid, name_map.get(cid, "")))
backlog += [
    "",
    "## Preserved immature set",
    "",
    "**39 genuinely immature** CAP-IDs (ABSENT/SPECIFIED excluding the seven above) preserved in baseline — build backlog, not auto-promoted.",
    "",
    "IDs:",
    "",
]
for cid in GEN:
    backlog.append("- `%s` (%s)" % (cid, name_map.get(cid, "")))
backlog_path = root / "docs/deliveries/MODEL-C-EVIDENCE-REMEDIATION-BACKLOG-2026-09-17.md"
backlog_path.write_text("\n".join(backlog) + "\n")

event = """# MODEL C NUMERIC CREDITS — LOCK EVENT

**Date:** 2026-09-17  
**Event:** Matt APPROVED — LOCK MODEL C NUMERIC MATURITY CREDITS  
**Version:** `%s`  
**Canon path:** `docs/MODEL-C-SYSTEM-NUMERIC-CREDITS.md`  
**Official baseline (docs only):** %s%% — NOT on dashboard  
**Displayed 28%%:** unchanged (legacy)
""" % (VERSION, pct)
(root / "docs/deliveries/MODEL-C-NUMERIC-CREDITS-LOCK-EVENT-2026-09-17.md").write_text(event)

cal = root / "docs/deliveries/MODEL-C-NUMERIC-CREDIT-CALIBRATION-2026-09-17.md"
ct = cal.read_text()
if not ct.startswith("> **PROMOTED"):
    cal.write_text("> **PROMOTED → CANONICAL CREDITS %s** — Mapping D locked. This calibration is historical evidence.\n\n" % VERSION + ct)

summary = {
    "version": VERSION,
    "reconcile": "PASS",
    "counts": dict(counts),
    "sum_credits": str(total),
    "exact_pct": str(exact),
    "rounded_pct": str(pct),
    "genuinely_immature": len(GEN),
    "under_evidenced": UNDER,
    "canon": "docs/MODEL-C-SYSTEM-NUMERIC-CREDITS.md",
    "backlog": str(backlog_path),
    "official_baseline": "docs/deliveries/MODEL-C-SYSTEM-BASELINE-OFFICIAL-2026-09-17.md",
}
(root / "docs/deliveries/MODEL-C-NUMERIC-CREDITS-LOCK-SUMMARY-2026-09-17.json").write_text(json.dumps(summary, indent=2))
print(json.dumps(summary, indent=2))

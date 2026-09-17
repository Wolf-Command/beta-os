# MODEL C — SYSTEM NUMERIC MATURITY CREDITS (CANONICAL)

**Status:** CANONICAL  
**Scoring model version:** `MODEL-C-SYSTEM-CREDITS-v1.0-2026-09-17`  
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
| ABSENT = 0% | No sufficient approved specification exists. |
| SPECIFIED = 5% | Wolf knows what the correct machine should be; documentation alone earns only token SYSTEM maturity. |
| BUILT = 25% | Locatable implementation exists, but until independently proven it remains substantially an implementation claim. |
| PROVEN = 80% | Deterministic verification plus required review/red-team has retired most technical implementation risk. |
| READY = 100% | Technical deployment/runtime/dependency proof is complete for the capability's intended boundary. READY is independent of human operating adoption. |

## Sanity checks (intentional)

If every canonical capability were only:

- SPECIFIED → SYSTEM = **5%**
- BUILT → SYSTEM = **25%**
- PROVEN → SYSTEM = **80%**
- READY → SYSTEM = **100%**

## Formula

Equal capability weighting. No domain weights. No hidden weights. No entity/venue adoption inside SYSTEM.

```
SYSTEM% = SUM(canonical capability maturity credits) / 77 × 100
```

Locked Requirement Credit applies only where an approved versioned partial-credit pack exists.

## Governance

Future credit changes require explicit Matt approval.  
Never tune credits to improve displayed %.  
Never silently rewrite historical scores when the model changes — keep versioned history.

## Version history

| Version | Date | Change |
| --- | --- | --- |
| `MODEL-C-SYSTEM-CREDITS-v1.0-2026-09-17` | 2026-09-17 | Initial lock (mapping D / verification-weighted). Prior candidate B not adopted. |

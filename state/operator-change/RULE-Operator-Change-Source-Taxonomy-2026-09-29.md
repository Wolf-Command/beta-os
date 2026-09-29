# RULE — Operator Change Source Taxonomy (2026-09-29)

**Status:** STANDING (Owner correction Matthew → Peaches, 2026-09-29 ~20:48 WITA)

**Applies to:** Operator change daily report, operator-change evidence under `state/operator-change/`, adoption / commissioning counters.

## Standing inequality

**V1 ACTIVITY ≠ BETA ACTIVITY ≠ HUMAN COMMISSIONING ≠ OPERATING ADOPTION**

Machine form: `state/operator-change/SOURCE-TAXONOMY.json`

## Classify by source system

| Class | Meaning | Counts toward Beta / Wolf adoption / staff_ready / human_commissioning / operating adoption? |
| --- | --- | --- |
| **V1_ACTIVITY** | Writes on current production / V1 (e.g. wolf-system HR board) | **NO** — preserve as V1 ops history / future migration source |
| **BETA_ACTIVITY** | Work inside Beta construction / beta-os | Only Beta activity (still ≠ commissioning / operating adoption) |
| **HUMAN_COMMISSIONING** | Explicit human commissioning loop for a Wolf capability | Only when that loop evidence exists |
| **OPERATING_ADOPTION** | Measured use of a commissioned Wolf capability at the canonical boundary | Only when adoption rules say yes |

## HR (Tisa) — current lock

- Current HR OS = **V1**.
- HR stays **OUTSIDE** current migration / commissioning scope until Owner explicitly moves it.
- Tisa HR journal edits = **SOURCE=V1** / **V1_ACTIVITY**.
- Do **not** treat local sync IDs-without-names as incomplete Tisa records (retrieval/sync gap; V1 authoritative).
- Do **not** invent staff names.
- Do **not** mark commissioning from V1 HR edits.
- Future HR migration: **reconcile latest V1 at cut line** so interim changes are not lost.

## 29 Sep 2026 corrected Tisa line

`Tisa (HR / SOURCE=V1): 132 edits + 17 new BZG staff (BZG26090006→BZG26090022). V1 ops history only. Not Beta / Wolf adoption / staff_ready / human_commissioning / operating adoption.`

Evidence: `state/operator-change/CORRECTION-20260929-tisa-v1.json`, `state/operator-change/REPORT-20260929.json`

## Reporter obligation

Every future Operator change daily report line MUST carry `source_system` / `source_class` so activity is not lumped into Beta, Wolf adoption, or commissioning by default.

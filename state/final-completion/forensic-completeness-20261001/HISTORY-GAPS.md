# History gaps
**Rule:** a count is tied to the store that produced it. Library ≠ NAS ≠ footage catalogue ≠ `nas_index`.

## Content media
| Store | Count | When / how | Class |
|---|---|---|---|
| NAS `01-Media-Library` shallow maxdepth 3 | **38,091** | Peaches sample, stamp ~2026-10-01 08:02 WITA. Pulse tile repeated it this session | HISTORY_AVAILABLE_NOT_INGESTED as a Wolf library |
| Peaches library assets figure | **18** | Sample, `CONTENT-STACK-TRUTH` / desk stamp. `full_tree_indexed=false` | Same stamp |
| `catalog/content_library.sqlite` `assets` | **48** (47 `indexed`, 1 `VERIFIED`; 39 `operational`, 9 `test`) | Read-only SQL this session | PARTIALLY_INGESTED. Later and larger than 18. Still not 38,091 |
| `nas_index` rows | **63,370** | Same sqlite | PARTIALLY_INGESTED index rows. Not proof every NAS file is a usable asset. `nas_duplicate_candidates` = 42,215 |
| V1 `state/footage-catalogue.db` `footage` | **61,719** | Read-only SQL this session | AUTHORITATIVE_ELSEWHERE (V1 catalogue). Beta library did not absorb it |
| Editable-3 / stock-1 | 843 / 207 | Peaches stamp, repeated on pulse | PARTIALLY_INGESTED slices |
| `content_cards` | 153 | sqlite | Wolf cards, not the NAS |
| `performance_records` | 1,103 | sqlite | Metricool-side history fragment. WRITE off, so it is not a learning loop |

`full_tree_indexed=false` remains the pulse honesty line. Do not describe 63,370 index rows as “the library is caught up”.

## Finance and buying
| Store | Count | Class |
|---|---|---|
| Alchemist `data/alchemist.db` ledger 473, petty 443, pr_orders 543, pr_receipt_lines 477, suppliers 103, purchase_requests 2 | V1 live sqlite this session | AUTHORITATIVE_ELSEWHERE. Beta pulse **reads** it. Beta `bzg_ops_petty_*` = 0, `bzg_ops_receipt_events` = 0 |
| Atrium sales sqlite leads 570, payments 399, units 88, cv_transactions 642 | V1 | AUTHORITATIVE_ELSEWHERE. Beta `core_leads` = 8 and the pulse says those fixtures were ignored |
| GGV `ggv_notas`, `ggv_invoices`, `ggv_vendors` | 0 in Beta catalog | HISTORY_AVAILABLE_NOT_INGESTED if V1 money sqlite holds them; not re-counted this pass. Beta side is empty |
| Xero | Connection matrix **ABSENT** | UNAVAILABLE as a Beta feed. V1 still has xero scripts and `/api/ggv/xero-final` |
| BZG July and August HTML boards | Files on V1 disk | WOLF_AUTHORITATIVE_FROM_CUT_LINE for those months. Not migrated |

## Hotel, guest, CRM
| Store | Count | Class |
|---|---|---|
| `state/reservations.db` | 1 reservation | HISTORY_AVAILABLE_NOT_INGESTED or never collected. UNKNOWN which. Absence is not “no guests” |
| `state/guest-profiles.db` | 1 guest, 1 visit, 2 observations | Same |
| Habitat sheet via pulse | 271 leads | AUTHORITATIVE_ELSEWHERE (Google Sheet). Not `core_leads` |
| Yanolja | Last read 2026-10-01 07:16, vacant vs rooms | WOLF_AUTHORITATIVE_FROM_CUT_LINE for that read. In-house history not in the pulse |

## Tasks, decisions, evidence
| Store | Count | Class |
|---|---|---|
| `core_work_items` | 211 | PARTIALLY_INGESTED Wolf queue. Not V1 wolf/amanda/mila desks |
| `core_approval_requests` | 0 | WRITE path empty |
| `core_audit_events` | 22,458 | Volume without a proved user history browser |
| `core_evidence_records` | 28 | Thin versus “court-battle evidence” in round 10 |
| `core_approval_decisions` | 9 | Not an approval system |
| Decision logs in vault and `wolf-output/decisions.md` | Files exist | AUTHORITATIVE_ELSEWHERE. Not a Beta decision card desk |

## F&B recipes
V1 and Beta recipe sqlite both show **127 / 756**. Treat Beta as a **copy of the recipe cards**, not as ingested theoretical-vs-actual history. `recipe_compare` on V1 is 0.

## Provenance line to keep
NAS file ≠ index row ≠ library asset ≠ footage catalogue row ≠ content card. Quote the store name with the number.

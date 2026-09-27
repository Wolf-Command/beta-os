# PROPOSED Uma variance policy

Status: **PROPOSED structure. Not loaded. Not active.** Thresholds **UNRESOLVED**. Owner brief 28 Sep 2026 06:46 WITA, item 3. No cash amount was written. The closer seat was not filled.

## What exists

`venue_close_variance_policies` requires `abs_threshold_amount` (`NOT NULL`) and defaults `currency` to `IDR` and `comparison_rule` to `LTE_INCLUSIVE`. Status is `ACTIVE` or `INACTIVE`. The live matcher in `scripts/core/venue_close.py` reads `status = 'ACTIVE'` only. Live row count is 0. That 0 is the row count. It is not a tolerance. The close page already says no variance policy is set.

A row cannot be stored with an unresolved amount. This proposal is not a row.

Petty variance is a different table (`bzg_ops_petty_variance_policies`). It was not seeded. Petty thresholds stay UNRESOLVED in the finance matrix.

## Proposed structure

| field | proposal |
| --- | --- |
| entity | `ENT-BZG` |
| venue | `BZG-UMA` |
| currency | UNRESOLVED. The column default `IDR` is not an approval |
| absolute threshold | UNRESOLVED |
| comparison | `LTE_INCLUSIVE` is the column default. Keep it only if you approve that rule. Otherwise UNRESOLVED |
| status when eventually stored | `INACTIVE` until you mark it active |
| who submits | `ROLE-BZG-CLOSER` or `ROLE-BZG-FB-OPS-LEAD` via `venue.close.submit` |
| who verifies | `ROLE-BZG-HFB` via `venue.close.verify`. Not the submitter |
| closer seat | `POS-BZG-CLOSER-UMA-1` stays empty. Who sits there is a separate human decision. This policy does not name a person |
| evidence | declared cash already requires evidence in the close machine. Keep that |
| over the threshold | state `VARIANCE_REQUIRES_POLICY`, then an exception and a work item. The exception does not invent a tolerance |
| no approved threshold | stay blocked. Do not treat missing policy as zero |

`ROLE-BZG-FB-OPS-LEAD` does not hold `venue.close.verify`. That stays. `ROLE-MATT` holds verify and submit; self-verify stays denied by `sod_self_close`.

ESB remains read-only. Settlement API stays unavailable. This policy does not write ESB and does not declare a cash figure.

## APPROVE / CHANGE — Matt

Mark one:

- [ ] APPROVE the structure only. Threshold, currency, and comparison stay UNRESOLVED. Do not insert a row until a threshold exists.
- [ ] CHANGE the structure. Write the change. An amount you do not set stays UNRESOLVED.
- [ ] NO VARIANCE POLICY. Mismatch stays blocked. That is already the live behaviour while the table is empty.

| field | your value, or leave UNRESOLVED |
| --- | --- |
| Currency | |
| Absolute threshold | |
| Comparison rule | |
| Submit role | |
| Verify role | |
| Closer person | leave blank. Not this policy |

Do not seat a closer on this page. Do not type a till count.

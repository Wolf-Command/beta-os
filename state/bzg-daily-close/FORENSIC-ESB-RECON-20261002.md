# FORENSIC — ESB live 61 / Rp 2,855,000 ≠ receipt 58 / Rp 2,735,000

**Pack:** BZG-CLOSE-OWNER-CONTROL-ESB-RECON-1  
**When:** 2026-10-02T22:39:34+08:00  
**Policy:** Do **not** overwrite live with receipt (or vice versa). Dual-source only.  
**Flags:** `staff_ready=false` · Daily Close NOT commissioned

## Verdict

| Delta | Live | Receipt | Exact cause |
| --- | ---: | ---: | --- |
| Bills | 61 Finished | 58 | **+3 OTHER COST** bills (COMPLIMENT + Executife Chef ×2), `billNum=null` — omitted on closing receipt |
| Pax | 106 | 103 | Same 3 OTHER COST bills (1 pax each) |
| Gross | 18,614,008 | 18,395,000 | Same 3 bills (Δ 219,008) |
| Cash | 2,855,000 tendered | 2,735,000 | **Change overpay** on 5 cash bills (Σ Rp 120,000). Receipt cash = cash-bill `grandTotal`, not tendered |

Bank EDC/QRIS lines (BNI/Mandiri) and non-bank comps (ROB / ROOM / SCOTT) **match** between live method names and receipt once QRIS is classified by `paymentMethodName`.

## Not the cause

- Date boundary / TZ cut — all rows `biz_date=2026-10-02`
- Cancels as the +3 — cancelled=5 are separate; the three extras are Finished OTHER COST
- Late post-print cash bill alone — the Rp 120k is distributed change overpay, not one missing bill

## Sources kept

- LIVE: warehouse payment lines (`esb.sqlite` RO)
- RECEIPT: Owner printed closing receipt (photo → vision → confirm path)

JSON: `state/bzg-daily-close/FORENSIC-ESB-RECON-20261002.json`

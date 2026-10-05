# Peaches forensic hint (do not overwrite sources)

See `FORENSIC-ESB-LIVE-VS-RECEIPT-20261002.json`.

- **61 vs 58 bills:** live `finished_count` includes 3 Finished `OTHER COST` rows with null `billNum`. Receipt bills = 58 = Finished with real `billNum`.
- **Cash +120k:** sole gap = `BLZ202610020031` CASH Rp 120,000. All EDC BNI/Mandiri + QRIS BNI/Mandiri + ROB/ROOM/SCOTT match receipt exactly.
- **Pax:** non-OTHER Finished pax = 103 = receipt.
- Classifier: bucket by `paymentMethodName` (QRIS before CARD); never lump QRIS into EDC.
- UI: dual source + difference board; receipt photo vision confirm; Owner Control audited.

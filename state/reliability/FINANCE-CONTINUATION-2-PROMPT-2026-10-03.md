Continue the Finance Control Repair pack on this Beta workspace. Do not treat the previous exit as finished.

Workspace: /Users/wolfterminal/beta-os
Beta is the only construction site. Serve it with the existing Beta launch agent on :8788.
Production :8787 python pid 15975 is sacred. Do not restart it, do not deploy to it, do not edit its database.

Already done. Do not redo and do not regress:
- Dated snapshot freeze: once a snapshot has a fingerprint, capture side-reads live ESB and does not overwrite stored API totals. Live cash 2,855,000 and printed receipt cash 2,735,000 both stay. Cause of the difference is not invented.
- History detail, range totals excluding CANCELLED/OPEN and superseded EDC.
- Local prove on a throwaway cancel only.
- Preserved close VDC-87202768-55af-4c8e-abc3-382a5496b8c6 stays DATA_CAPTURED, holder PERS-MATT. Do not cancel, reopen, or mutate it.
- GGV vault read-only list GET /api/ggv/finance/receipts and the existing receipt bridge. Do not build a second receipt pipeline. Do not revive Xero.

Checkpoint: state/reliability/FINANCE-CONTROL-CHECKPOINT-2026-10-03.md
Mission context: state/reliability/FINANCE-CONTROL-REPAIR-2026-10-03.md

Finish the remaining approved Finance Control Repair scope, reusing what exists. For each item, make it work on the running Beta, then prove it against the running Beta process and its real database. Repository tests alone are not proof. A page render is not proof.

Required outcomes:
- Closing history a staff or owner user can open on the real Uma Blu close screen, including a historical date and a date range, with range totals from saved rows.
- Add a missing historical close for a business date, pulling that date's ESB, not today's live ESB.
- Three objects stay separate: live ESB, dated close snapshot, final historical close. Live ESB and the printed closing receipt stay separate. Do not force them to match.
- Cancel an unfinished close, restart that cancelled close, and reopen a completed close while the original history stays immutable. Use throwaway rows only. Never the preserved close above.
- Owner takeover and reassignment, audited.
- Two people cannot hold two current closes for the same outlet and business date.
- Full ESB receipt extraction, including dynamic unknown lines. Mandiri, BNI, and BRI stay separate EDC cards. EDC and QRIS reconcile separately. NOT USED TODAY is a real state, not zero. A corrected terminal receipt supersedes the old one and the old one stays in history.
- If vision extraction fails, the person can enter the figures by hand. Do not invent a Mandiri photo for the preserved close.
- GGV: Peaches receipt text can be filed through the existing bridge into Accounting. Original receipt images stay evidence. Accounting screens for receipts, missing evidence, and review must show real vault data, not fixtures.
- Bank statement upload keeps the original file and writes normalised transactions. Matching and reconciliation work on those rows. Missing evidence is visible. An accountant sees only their entity. AMG, BZG, and GGV data, books, and authority stay separate.
- Owner controls that exist as API get a real control on the close screen where the owner is the one who uses them. Every important change is audited: who, what, when, before, after.
- Entity isolation holds. Zayen is not given GGV finance.

Do not start BZG Procure to Pay. Do not commit or push. Leave the tree dirty if that is the current practice, and append what you actually proved to the checkpoint file. staff_ready stays false. eng_proved stays false unless you verified the running Beta, not just unit tests.

Done means: the running Beta on :8788 shows the behaviours above with persisted rows, production pid 15975 is unchanged, and the preserved close is unchanged.

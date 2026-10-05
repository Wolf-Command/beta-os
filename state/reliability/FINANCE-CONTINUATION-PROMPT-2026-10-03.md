You are the single Finance Control Repair continuation on Beta only.

Workspace: /Users/wolfterminal/beta-os
Branch: build/wolf-command-rebuild
Do not push. Do not merge PR #1. Do not mutate prod. Prod is com.wolfcommandsystem.dashboards-serve pid 15975 on :8787. Do not restart it. Do not kill Grok Bot. Do not start BZG Procure to Pay. Do not install SSH, Tailscale, or the Wolf Recovery Key. Do not print environment variables, process arguments, or API keys. Do not spawn another cursor-agent.

Read first, then continue. Do not start from zero:
- /Users/wolfterminal/beta-os/state/reliability/FINANCE-CONTROL-CHECKPOINT-2026-10-03.md
- /Users/wolfterminal/beta-os/state/reliability/FINANCE-CONTROL-REPAIR-2026-10-03.md

Owner amendment stands:
- Owner authority is audited UI control. Wolf controls staff. Matt controls Wolf.
- Three different objects: live ESB operational data, dated closing snapshot, final historical close.
- Live API and printed receipt never overwrite each other. Do not force the 2 Oct 2026 figures to agree and do not invent a cause.
- Receipt model is RECEIPT, SECTION, LINE. Unknown lines stay NEEDS CLASSIFICATION.
- Three Uma Blu bank cards from outlet config: MANDIRI, BNI, BRI. One current reconciliation state. Superseded attempts stay in audit and are excluded from totals.
- Vision is a Wolf capability, not a staff Gemini feature. Staff never see provider or key errors.
- Cancel unfinished abandons the draft only. It does not touch history or accounting.
- No READY FOR MATT TEST. staff_ready stays false. eng_proved stays false. Cursor exit is not PASS. Code complete is not ENG_PROVED.

Last proved slice, already done, do not redo and do not declare PASS:
History date filters, closing_history from saved rows only (live_esb_used=false), cancel_unfinished_close, Beta routes on :8788, uma-blu-close history UI. Classification of that slice: CODE COMPLETE / INTEGRATION UNPROVED. Last noted tip was 0b0e50d and the tree was dirty. Inspect the current tree. Do not declare PASS from git status.

Preserve this close and its receipt photos. Do not cancel it. Do not change its holder or state:
VDC-87202768-55af-4c8e-abc3-382a5496b8c6
business date 2026-10-02, outlet BZG-UMA, state DATA_CAPTURED, holder PERS-MATT.
Mandiri on that close stays RECEIPT_REQUIRED unless a real terminal photo already exists. Do not invent one.
EDC bank cards remain CODE_COMPLETE_AWAITING_PEACHES_VISUAL. Do not clobber that work and do not call it Matt-ready.
Do not edit scripts/mac-reachability or HA-WATCHDOG-TARGET-2026-10-03.md.

Do the next unfinished approved slice, in this order:
1. Three-object close. An open dated snapshot must not be mutated by live ESB sync. A backdated close uses that business date, never today's live sales. Final close stays historical evidence. Keep API figures and printed receipt figures as separate retained sources, with the difference visible.
2. History detail. Show source snapshot, API vs receipt difference, bank-by-bank EDC, QRIS, cash, non-sales, evidence, and corrections. Range totals use finalized/current states only, not superseded attempts. Cancel unfinished still must not rewrite history.
3. Extend the existing local prove. Use a throwaway close for any cancel test. Re-check that VDC-87202768 is still DATA_CAPTURED and still holder PERS-MATT afterwards.
4. Only after 1-3 are in the tree and locally proved, inspect the existing receipt intake (receipt-from-telegram.py, receipt-ingest.py, and any Beta successor) and continue Part B GGV by reuse. Do not build a second pipeline. If GGV cannot be finished in this run, stop after a real increment and say what is left.
5. Append this run to FINANCE-CONTROL-CHECKPOINT-2026-10-03.md. Do not erase the last-proved section. Leave staff_ready=false and eng_proved=false. Do not write READY FOR MATT TEST.
6. Do not commit and do not push. The proved tip was dirty on purpose. Leave the working tree dirty and record the new state in the checkpoint.

Beta :8788 may be restarted only through its existing LaunchAgent if a route change cannot be seen otherwise. Afterwards, confirm prod pid 15975 is still the listener on :8787. If it is not, stop and do not try to repair prod.

# BZG-P2P-GRANT-REPAIR-1

You are the single Beta writer for this slice. Workspace `/Users/wolfterminal/beta-os`. Today is Monday 5 Oct 2026, Asia/Makassar (WITA, UTC+8).

Title: Repair BZG P2P pay-ready overgrant

Finding: BREACH-2026-10-05-J1-BZG-P2P-PAY-READY-OVERGRANT. Status is open RED.

Evidence file (read it before you edit): `state/lanes/breach/findings/2026-10-05-j1-quiet-probe-red-bzg-p2p-pay-ready-overgrant.md`

If that Beta path is absent, the possessed copies are:
- `/Users/wolfterminal/.openclaw/workspace/wolf-system/state/lanes/breach/findings/2026-10-05-j1-bzg-p2p-pay-ready-overgrant.md`
- `/Users/wolfterminal/2026-10-05-j1-quiet-probe-red-bzg-p2p-pay-ready-overgrant.md`

Do not treat a missing Beta path as a closed finding. The RED stays open until the acceptance denies below are proved.

## Repair

Replace the copy-from-`work.complete` grants for these permissions with an explicit role matrix:

- `bzg.po.create`
- `bzg.bill.capture`
- `bzg.match.run`
- `bzg.ap.view`
- `bzg.ap.mark_ready`
- `bzg.pay.list_ready`
- `bzg.pay.mark_ready`

Segregation of duties: the person who created the PO or recorded the nota cannot mark that same document pay-ready.

Make `bzg.ap.*` and `bzg.pay.*` entity-bound so `SCOPE-WOLF-CONTENT-ALL-BRANDS` cannot ALLOW a BZG entity target.

Haikal, Misa and Yudi must be DENIED on BZG-UMA, BZG-RAIN and OU-BZG-RAIN-POOL for `pay.mark_ready`, `ap.mark_ready`, `po.create`, `bill.capture`, `pay.list_ready`.

Captain (Iza) and Head Chef (Haryanto) must not be able to complete the chain alone. A person who created the PO or recorded the nota is DENIED `bzg.ap.mark_ready` and `bzg.pay.mark_ready` on that same document. Live proofs: PERS-IZA on BZG-UMA and PERS-HARIYANTO on BZG outlets must not hold create + capture + pay-ready together.

## Do not grant

Do not grant `payment.execute`, `payment.approve`, `bzg.pr.payment_approve`, or `vendor.bank.change`.

## Do not touch

- Keep petty as-is: Captain `record_out` only; `record_in` and reconcile stay Owner and BZG financial controller.
- Do not touch `PETTY-UMA-6D853EEAE0`. Balance must stay Rp552,700.
- Do not mutate closes VDC-470e741f, VDC-64f5f529, VDC-8fd544e2.
- Do not edit uma-blu-close or daily close code.
- Do not edit daily close, petty, or protected close rows.
- Prod untouched. Do not touch production (pid on 127.0.0.1:8787).
- `staff_ready` false. Do not mark human commissioned.
- Do NOT reload the Beta listener. Leave the pid on 8788 running. Matt is on the 29 Sep close page. A reload would interrupt him.
- Tests must run without a reload. If a reload would be required, stop and report `RELOAD_HELD`.
- Do not commit, push, merge, or clean the dirty tree.
- Do not kill other workers. Do not take a second writer if one is already live.

## Tests

Add regression tests for:

1. GGV content deny: PERS-HAIKAL, PERS-MISA, PERS-YUDI DENY `bzg.po.create`, `bzg.bill.capture`, `bzg.ap.mark_ready`, `bzg.pay.list_ready`, `bzg.pay.mark_ready` on BZG-UMA, BZG-RAIN, and OU-BZG-RAIN-POOL. `SCOPE-WOLF-CONTENT-ALL-BRANDS` must not satisfy a BZG finance target.
2. One-person chain deny: the PO creator or nota recorder cannot mark that same document pay-ready. Captain (Iza) and Head Chef (Haryanto) cannot complete the chain alone.

Pass = both DENY. Fail = either ALLOW. Do not prove this by copying `work.complete`.

## After you exit

Do not describe AP or Ready to Pay as ready for human test. After the worker exits, Peaches recounts before anyone is told it is testable. Until then AP and Ready to Pay are NOT ready for human test.

Write a result file under `state/reliability/` for this slice id. Do not delete existing `BZG-P2P-AP-1` or `BZG-P2P-READY-TO-PAY-1` result files.

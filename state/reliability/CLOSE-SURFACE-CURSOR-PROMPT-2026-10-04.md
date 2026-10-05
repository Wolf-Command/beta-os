# Daily Close staff surface — 4 Oct 2026

You are editing ONLY /Users/wolfterminal/beta-os.

This slice is the human Daily Close surface. Finish it from behavior already built this morning, then stop. Do not start FCR-GGV-41. Do not add any new backend field, table, route family, or product. Do not invent a second close system.

## What to change

Wire the already-built Daily Close behavior into the existing staff page `dashboards/uma-blu-close.html` and the existing `scripts/serve_beta.py` routes that already call `scripts/core/bzg_daily_close.py` (and the venue-close helpers that page already uses).

Staff language only. The page a closer sees must follow this flow and no other:

1. Open today's close.
2. Photograph the shift report.
3. Confirm the extracted figures.
4. Mandiri, then BNI, then BRI: photograph or enter the terminal totals.
5. Photograph or count the cash.
6. Wolf compares the sources and shows plain-language differences.
7. Resolve or explain each difference.
8. Submit once.
9. One unmistakable result.

No internal IDs on screen. No provider names. No second submit control. No button labeled Reconcile, and no other control that could be confused with submit. There is one submit.

Keep three sources distinct in the words and the comparison: live ESB, the printed shift receipt, and the physical till. Never collapse them into one number. Never label the 3 Oct Rp125,000 gap as a physical cash shortage.

## Morning behavior — surface only

Do not rebuild these. They already exist. Show them only where they change what staff see or what submit does:

- Reopen chain (FCR-BZG-12): if a close is reopened, staff see that the original stands, what changed, and that a new approval is required. Not stage names, not table names.
- Idempotent submit (FCR-BZG-16): submitting again with the same figures does not create a second close. Say so in plain language. A different amount is not a silent success.
- Wrong-date rejection (FCR-BZG-17): a photo or submit for a different date is refused in plain language and does not change today's close.
- Audit trail (FCR-BZG-18): staff can read a plain history of what happened to this close. No raw event names, no person-id strings, no JSON.
- Original receipt kept (FCR-BZG-19): when a later receipt replaces an earlier one, the original photo is still there and labeled as the earlier one.
- Unknown lines (FCR-BZG-22): a line that is not understood is shown as needs classification. It is not dropped and not forced into cash or card.
- Mandiri, BNI, BRI (FCR-BZG-23): those three come from outlet configuration. If configuration is empty, the page says needs setup. It does not show zero.
- Failed photo (FCR-BZG-28): if a photo cannot be read, the close stays open and typed entry is available.

A missing bank amount stays blank. Never display it as zero.

If a control is not ready, hide it. Do not show a dead or disabled button.

Permissions stay assignment-based. Do not hardcode Iza or any email address. Do not set BETA_AUTH_MODE.

## Do not touch

- Do not read or write close VDC-470e741f-d889-437a-9a40-1ec9c083fb95.
- Do not read or write close VDC-87202768-55af-4c8e-abc3-382a5496b8c6.
- Do not use the 3 Oct close as a test.
- Tests use a schema-only or tiny temporary sqlite created by the existing schema helper. NEVER shutil.copy2 the live catalog `catalog/content_library.sqlite`. NEVER vacuum or backup that file. NEVER write `catalog/backups`. NEVER write the live catalog. If a test would require that copy, stop and write the result as BLOCKED_DISK with no copy made.
- Do not restart Beta. Do not signal pid 93525. Do not signal production pid 15975. Do not reload either process.
- Leave pid 63443 alone.
- Do not commit, push, merge, reset, stash, or clean.
- Do not put secrets or process command lines in any file.

## Done

py_compile Python you edit. Run one new or existing temp-sqlite test that proves the staff-visible rules you wired (blank bank is not zero, empty outlet banks say needs setup, failed photo still allows typed entry, repeat submit is not a second close). Do not claim the page was commissioned by a person.

Write `state/reliability/CLOSE-SURFACE-RESULT-2026-10-04.md` with files changed, what staff now see, test command, pass/fail counts, what you did not change, and status IMPLEMENTATION_DONE, BLOCKED, or BLOCKED_DISK.

Stop when that result file is written.

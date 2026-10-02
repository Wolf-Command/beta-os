# Haikal Content Engine human feedback — Cancel Upload

**Date:** 2026-10-02 WITA  
**Origin:** Haikal (Creative Director) — Content Engine human commissioning  
**Owner:** Matthew Goss — **APPROVED**  
**Status:** ACCEPTED → Cursor implements on Beta; Peaches verifies (credit-light)  
**Prod:** UNTOUCHED

## Feedback (verbatim intent)

> Can we add a Cancel button while files are uploading, in case we notice the wrong brand, wrong stage, or accidentally queued the wrong footage?

## Canonical behaviour (Owner-approved)

### Cancel while batch actively processing
- Clear **Cancel Upload** at **batch** level and, where practical, **per-file**.
- Respect real asset lifecycle (do not fake cancel after commit).

### BEFORE file storage starts
- Cancel immediately; remove from queue.
- No NAS file; no Library/index record.
- Status: `CANCELLED`

### WHILE transferring
- Abort transfer safely if possible.
- Remove incomplete temp file; never leave partial media as a valid asset.
- Status: `CANCELLED`

### AFTER safely stored on NAS
- Do **not** pretend upload was cancelled.
- Stop subsequent processing where safe.
- Tell user: **File already uploaded. Processing stopped.**
- Offer governed correction: Edit details / Move brand·stage / existing correction workflow.
- Do **not** auto-delete committed originals because Cancel was late.
- Historical preservation > magical Cancel.

### Wrong brand / wrong stage (primary Haikal use case)
- After upload, authorised Content staff can correct metadata (brand, stage, content type, subject, location, details) where policy allows.
- Audit trail: old value, new value, person, timestamp.
- No duplicate/re-upload merely to fix metadata.

### Batch UX during upload
Show: overall progress, current file, completed / remaining / failed / cancelled counts, Cancel Upload.

Cancel batch:
- stop not-yet-started
- abort current transfer where possible
- never disturb successfully committed files
- report e.g. `7 uploaded · 1 stopped during processing · 6 cancelled before upload` (not bare “Cancelled”)

### Confirmation
- No per-file confirm spam.
- One batch confirm:  
  **Cancel remaining uploads?**  
  Files already uploaded will stay in the Library.  
  [Keep Uploading] [Cancel Remaining]

## Engineering proof (Cursor tests)
cancel queued before upload; cancel batch before first file; cancel mid-transfer; temp partial cleanup; cancel after stored (asset preserved); no duplicate Library/NAS; cancelled ≠ READY; completed intact; metadata correction + audit; retry unaffected; multi-file MOV batch.

## Haikal retest (fold into existing Content commissioning — not a disconnected round)
1. Start small 3-file upload.
2. Cancel while running.
3. Confirm remaining stop correctly.
4. Confirm completed remain in Library.
5. Start upload with deliberately wrong Stage.
6. Correct Stage without re-upload.
7. Confirm search/filter reflects correction.

**Content Upload remains uncommissioned** until upload/search/cancel workflow passes human testing.  
`staff_ready=false` until then.

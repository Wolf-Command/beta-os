# SPEC — GGV Finance Mobile Nota + Vendor Workflow — 2026-09-24

**Run:** `BF-ggv-finance-mobile-nota-20260924`  
**Branch:** `build/wolf-command-rebuild` · soft head `f3ab8f7` (do not destroy uncommitted work)  
**Workspace:** `/Users/wolfterminal/beta-os` · Beta :8788 only  
**Prod:** :8787 sacred — **do not mutate** (PID often 15975)  
**RULE:** `docs/RULE-GGV-Finance-Mobile-Nota-2026-09-24.md`  
**AUDIT:** `docs/deliveries/AUDIT-GGV-Finance-Mobile-Nota-Reuse-2026-09-24.md`  
**CR:** `state/completion-register/ggv-finance-mobile-nota-20260924.json` · CAP **SPECIFIED** · **staff_ready=false** · **commissioned=false**  
**Class:** Owner operational replacement under Credit Conservation (`credit_conservation_exception=owner_operational_replacement`). One coherent pack. No broad Finance rebuild.  
**Recorded:** 2026-09-24 10:56 WITA

## Goal
Build GGV Finance inside Wolf so Matt and Amanda can run notas/bills on phone as the operating interface. Telegram nota retires **only after both humans commission**. Wolf must function without Telegram. No TG sync. No competing ledgers vs Zayen.

## Target UX
**WOLF → GGV → FINANCE → NOTAS / BILLS**

Flow: **UPLOAD NOTA → read info → identify/search vendor → select existing OR create new → confirm/correct → attach evidence → submit → status/history**

Minimum clicks. Mobile first. Desktop too. No engineering jargon.

## Nav (simple staff)
**OVERVIEW | NOTAS / BILLS | VENDORS | HISTORY**

Do not create ten empty finance pages. Wire into existing Wolf shell / GGV grammar (Finance is currently EMPTY — make this the live Finance entry for GGV staff).

## In scope

### 1. Surfaces
- GGV Finance staff desk on Beta with four tabs above
- Overview dashboard from **real data only**: Needs review, Waiting approval, Unpaid/payment-unverified, Recently added, Vendor issues — **no fake P&L/cash/AP ageing**
- Notas / Bills list + detail
- Vendors list + detail (canonical Vendor Master surface for GGV scope)
- History / search

### 2. Mobile upload
- **+ Upload Nota:** camera, photo, PDF/file, multiple supporting images
- Progress honesty: **Uploading → Reading document → Checking vendor → Ready for review → ✓ Saved**
- Failure: what failed, what preserved, retry. **Do NOT re-upload nota** if a later step fails (preserve uploads + extracts)

### 3. Extraction
Only what evidence supports: vendor name, nota/invoice #, date, total, tax, line/items, currency, payment/bank as **SOURCE EVIDENCE ONLY**.  
Every field = proposal for confirmation unless deterministic rules allow. Low confidence visible. Never invent missing amounts. No raw OCR internals on review screen.

### 4. Vendor matching + create inline
- Search canonical Vendor Master
- "We think this is: [Vendor]" + matches → **USE EXISTING** or **+ CREATE NEW**
- If none: Vendor not found + Create new — **no dead-end**
- Inline create (do not leave workflow): name required; category/contact/phone/email/tax/address/notes optional; UNKNOWN ok; no fake data
- On save: ✓ Vendor created → return to same nota with Vendor ID; preserve uploads + extracts
- Duplicate vendor protection: normalized name, phone, email, company/tax id → Possible existing vendor → Use existing OR Create separate with reason — **never silent merge**

### 5. Bank details boundary
**BANK DETAILS OBSERVED ≠ BANK DETAILS VERIFIED.** Captured as source evidence only. Bank create/change = separate controlled path (out of this pack's execute path). **NO money movement.**

### 6. Nota review screen
Vendor, invoice #, date, amount, tax, currency, category, items, attachment preview, notes, confidence/missing only where action needed. **SAVE / SUBMIT.** Human language.

### 7. Duplicate nota detection
file hash, vendor, invoice #, date, amount → Possible duplicate + existing record → user decides with audit. No silent reject/duplicate.

### 8. After submission — record shape
Canonical Wolf GGV finance/AP record **OR** explicitly compatible bounded record pending Zayen reconcile. Must have:
- Wolf record ID
- vendor ID
- source attachment
- creator
- timestamp
- amount/date confirmed
- workflow state
- history
- audit

Simple states **only where model supports**: Needs Review, Ready, Waiting Approval, Approved, Paid — Claimed, Payment Verified. Do not invent policy to fill states.

### 9. Payment boundary (hard)
**NOTA ENTERED ≠ APPROVED FOR PAYMENT ≠ PAID ≠ PAYMENT VERIFIED.**  
No bank write. No payment execute. No invented monetary limits. Operating permissions ≠ banking/payment authority.

### 10. Vendor Master
**ONE** vendor master in Wolf. Not separate TG / BZG / Finance-page / Nota-upload lists. Support entity/scope relationships. Don't force uncertain cross-entity merges. Do not import Telegram/Xero maps as verified without human confirm.

### 11. History / search
By vendor, date, amount, status, invoice #, category. Tap → attachment, details, vendor, history, evidence, actions.

### 12. Identities / permissions
Authorised: Matt, Amanda via **EMAIL → AuthIdentity → Person → Role → Assignment → Scope → Permission**.  
**NO hard-code names in UI auth.**

Add (or map) permission codes:
- `finance.nota.read` / `create` / `edit`
- `vendor.read` / `create` / `edit`
- `evidence.create` (may map to `evidence.record.submit` if cleaner — document mapping)

Keep separate from: `payment.approve` / `payment.execute` / `vendor.bank.change` / `finance.policy.admin`

### 13. Telegram
- Engineering: Wolf works **without** Telegram
- Do **not** sync Wolf→TG
- Do **not** create new TG vendor/nota records from this pack
- Historical TG evidence stays historical (`~/.openclaw/workspace/alchemist/*` is reference only)
- Do **not** mark Telegram RETIRED in code / claims until **both** Matt + Amanda human commissioning PASS (Peaches cards after engineering pass)

### 14. Tests + review artifact
- Permission tests: Matt allowed, Amanda allowed, unrelated staff denied, anonymous denied, client denied, typed hidden URL denied, APIs same policy
- Mobile acceptance tests (automated where possible + checklist): login, GGV→Finance, camera/PDF upload path, progress, vendor match/create, dup warnings, review, edit, submit, history, search, detail, back/up; no horizontal scroll dependency; no tiny desktop forms; no eng jargon
- Write `docs/deliveries/GROK-REVIEW-GGV-Finance-Mobile-Nota-2026-09-24.md`
- FAIL=0 on pack tests
- Restart Beta :8788 only if needed via existing helpers — **never** touch prod :8787

## Integration boundary with Zayen (document in code + GROK-REVIEW)

| This pack (bounded AP/evidence) | Zayen later (reserved) |
|---------------------------------|------------------------|
| Nota intake, vendor master ops for AP evidence, workflow states for review/approval *where supported* | Full Finance: reconciliation, cash, P&L, AP ageing, payment execute, banking verify |
| Compatible record IDs + audit + amounts confirmed | Canonical ledger / money movement |
| No competing ledger | Single finance truth |

Document the boundary in the Finance overview (human language: "Payment and full books live with Finance reconciliation later — here you capture notas and vendors.") — no eng jargon, no fake numbers.

## Acceptance — Owner questions (staff answers without Wolf architecture)
1. How do I open GGV Finance Notas / Bills?
2. How do I upload a nota from my phone (camera/PDF)?
3. How do I see upload/read/vendor progress?
4. How do I confirm or correct what was read?
5. How do I pick an existing vendor or create one without restarting?
6. What happens if the vendor might already exist?
7. What happens if this nota might be a duplicate?
8. How do I submit and find it later (history/search)?
9. Can I tell that entering a nota is **not** the same as paying it?
10. As unrelated staff / anonymous / client — am I correctly denied (UI + API)?

## Out of scope
- Production / :8787 mutation
- Broad Finance rebuild / speculative accounting / fake cash/P&L/AP ageing
- Payment approve/execute / bank write / vendor.bank.change execute path
- Retiring Telegram in code as end-state before both humans commission
- Wolf↔TG sync or new TG records
- New agents
- Marking PROVEN / READY / STAFF READY / commissioned
- Destroying soft-head uncommitted work
- Ten empty finance pages / competing ledgers
- Arming a second heavy pack

## Honesty locks
`proven=false` · `ready=false` · `staff_ready=false` · `commissioned=false` in state/CR.  
Telegram retire gate: `telegram_retire_only_after_commissioning=true`.  
Human commissioning stubs only — Peaches parent owns My Commissioning cards after engineering pass.

## Credit conservation
Owner exception run_id `BF-ggv-finance-mobile-nota-20260924` allowed. `pack_veto` still blocks **other** breadth. Haikal CE UX retest remains human waiting. Smart Upload after CE UX.

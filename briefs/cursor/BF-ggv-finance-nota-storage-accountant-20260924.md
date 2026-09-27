# Cursor brief — BF-ggv-finance-nota-storage-accountant-20260924

Read and execute:
`docs/deliveries/SPEC-ADDENDUM-GGV-Finance-Nota-Storage-Accountant-2026-09-24.md`

Also obey:
- `docs/RULE-GGV-Finance-Mobile-Nota-2026-09-24.md` (ADDENDUM Owner lock 2026-09-24 ~12:51 WITA)
- Gap audit `docs/deliveries/AUDIT-GGV-Finance-Nota-Storage-Gap-2026-09-24.md`
- Gate `state/build-factory/GATE-ggv-finance-nota-storage-accountant-20260924.json`

## Constraints
- Workspace `/Users/wolfterminal/beta-os` · branch `build/wolf-command-rebuild`
- Soft head `f3ab8f7` has uncommitted work — do not destroy it; Beta only
- Production :8787 sacred — do not mutate (PID must stay)
- No `--trust`; do not invent staff_ready/commissioned/Telegram RETIRED
- No new agents; no speculative breadth; no PR merge; no Wolf↔TG sync
- CAP / CR stay SPECIFIED; staff_ready=false; commissioned=false
- Payment/banking authority out of execute path
- Zayen full Finance reserved — document integration boundary; no competing ledger
- Credit conservation exception: this Owner-named arch correction ONLY
- Do NOT release Matt/Amanda commissioning HOLD; do NOT ping Matt FINISHED

## Scope (bounded)
1. Migrate canonical store from `state/ggv-finance-nota/blobs` → NAS `/Volumes/01-Media-Library/Finance/GGV/Notas/YYYY/MM` (reuse MEDIA_LIBRARY root; do not invent second root)
2. Wolf DB remains index/metadata; extend file metadata + `backup_state` enum honesty (UNKNOWN/PENDING until real B2 proof — never fake BACKED UP)
3. Preserve all evidence (migrate existing blobs if any; count was 0 at audit)
4. Year → Month → Nota History views without mutating evidence
5. MONTH EVIDENCE PACK export ZIP (product only; NOT canonical storage)
6. Seed ROLE + permissions for GGV EXTERNAL ACCOUNTANT (do not invent a real person); wire page/API/search deny outside GGV Finance scope
7. Optional thin Accountant tab only if reuse is cheap; no fake totals
8. No auto ZIP storage; no auto delete; no payment; Beta only

## Deliver
1. Implementation per SPEC on Beta
2. Tests FAIL=0 covering storage path, metadata, no-blob-only-in-DB, accountant deny matrix, backup_state honesty, year/month views, export pack (+ parent regression)
3. `docs/deliveries/GROK-REVIEW-GGV-Finance-Nota-Storage-Accountant-2026-09-24.md`
4. End with `EXIT: SUCCESS` or `EXIT: FAIL` and PASS=/FAIL= counts

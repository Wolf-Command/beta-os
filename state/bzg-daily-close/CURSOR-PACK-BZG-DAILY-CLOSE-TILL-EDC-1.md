# CURSOR PACK — BZG-DAILY-CLOSE-TILL-EDC-1 (Beta only)

Workspace: `/Users/wolfterminal/beta-os`  
Branch: `build/wolf-command-rebuild` (local only — **no origin/push**)  
Prod `:8787`: **READ-ONLY**. Never mutate prod.  
`staff_ready=false` · `human_commissioned=false` until Devi PASS after eng PASS.

Owner order: `state/bzg-daily-close/OWNER-ORDER-BZG-DAILY-CLOSE-TILL-EDC-20261002.json`  
Telegram recovery: `state/bzg-daily-close/TELEGRAM-PROCEDURE-RECOVERY.md` (+ `.json`) — status **TELEGRAM_SOURCE_INCOMPLETE** for Desktop chat; procedure from Alchemist `/nightly`.  
Gaps: `state/bzg-daily-close/GAP-VS-UMA-DAILY-CLOSE.md`

## Goal

One reusable **BZG Daily Close** engine (reuse Uma Blu Daily Close foundations — **do not new app**). Outlet config for all 7 Owner outlets; **only Uma Blu** human-activated now. Till + EDC per terminal with evidence binding. Mobile-first close. Exception Work Items. Variance requires review **without** invented tolerance. Settlement API honesty: **UNAVAILABLE** unless you prove otherwise. After Peaches eng PASS → Devi real close commission (Assignment/Role/Scope — **do not hardcode Devi**).

## Read first (reuse)

- `docs/canon/UMA-BLU-DAILY-CLOSE.md`
- `scripts/core/venue_close.py`, `scripts/core/esb_close_snapshot.py`
- `scripts/migrations/021_uma_blu_daily_close.sql` (+ migrate script)
- `scripts/tests/test_uma_blu_daily_close.py`
- `dashboards/uma-blu-close.html` + `/api/venue-close/*`
- WAVE2-01 declared-cash pack; PACK-02 Uma buy→close
- `scripts/core/bzg_outlet_registry.py` + `docs/canon/build-dashboard/Brands_Locations.csv`
- Authorised TG-bot procedure: `~/.openclaw/workspace/alchemist/nightly_cmd.py` (read-only reference — do not deploy Alchemist)

## Owner implement requirements (§§2–16 condensed)

1. **ONE engine** — extend `venue_close` / shared tables; no seven apps; no greenfield close product.
2. **Outlet config for all 7** (Owner list): Uma Blu; Blu Zone Rainforest Restaurant & Bar; Pool Bar; Merah Underground; Rooftop Bar; Room Service; Catering — drive from **canonical registry**, map display names; mismatches → visible **NEEDS CONFIGURATION** (do not hardcode seven forever).
3. **Human-activated close: Uma Blu only.** Other outlets config-present, activation false.
4. **Till close** — declared physical cash + **POS/Z-report evidence**; declared ≠ verified; do not copy ESB cash into declared.
5. **EDC close per terminal** — capture settlement slip evidence (photo/file) + acquirer/bank label + batch total + optional txn count; Card Total = Σ EDC batches when present; **ESB payment totals ≠ EDC settlement evidence**.
6. **Terminal registry** — config rows per outlet; Uma terminals unknown → **NEEDS CONFIGURATION** (do not invent IDs/counts). UI must show incomplete config honestly.
7. **Mobile-first** close UX (phone commission path for Devi after eng PASS).
8. **Evidence binding** — every till declare and every EDC line bound to Core Evidence / stored proof; no orphan amounts.
9. **Exception Work Items** on variance / policy / missing evidence — Assignment/Role/Scope to HFB / closer roles (existing SoD: resolver ≠ sole verifier; submitter ≠ verifier).
10. **Variance** — any non-zero declared−ESB_CASH_FROM_PAYMENTS requires review; **no invented tolerance**; do **not** seed ACTIVE `venue_close_variance_policies` from Alchemist’s soft 2%/Rp5k OCR warn.
11. **Settlement API** — remain `UNAVAILABLE` / PENDING_BANK unless you prove a real settlement read this pack; never fake bank match.
12. **Float** — Owner decision 2026-08-02: Rp 1,000,000 till float excluded from deposit/takings equation — config citation OK; do not invent other floats.
13. **RBAC** — `ROLE-BZG-CLOSER` submit; `ROLE-BZG-HFB` exception resolve+verify; `ROLE-MATT` as today; **no `if Devi`**; commissioner is Assignment seat.
14. **Engineering proof** — tests + RESULT under `state/final-completion/.../BZG-DAILY-CLOSE-TILL-EDC-1-RESULT.*` covering list below.
15. **After Peaches credit-light verify PASS** — Devi real Uma close on Beta → PASS/FAIL; not commissioned for config scaffolding alone.
16. **Do not drop** Recipe / Haikal Cancel fold / forensic / finance human waits; stamp only; no Exit Report; no Intelligence; prod untouched.

## Engineering proof (must cover)

- Single engine + registry-driven outlet config; only Uma `human_close_enabled`
- Till declare refuses ESB-copy; declared≠verified honesty flags
- EDC per-terminal evidence path exists; empty terminal config → NEEDS CONFIGURATION visible (no invented terminals)
- ESB snapshot still payment-lines basis; settlement_api UNAVAILABLE unless proved
- Variance≠0 → VARIANCE_REQUIRES_POLICY / exception; zero ACTIVE tolerance policies unless Owner-seeded (do not seed)
- Exception Work Item + SoD preserved
- ROLE-BZG-CLOSER / HFB via Assignment — no hardcoded Devi
- Mobile-first Uma close reachable on Beta `:8788`
- Tests green; local commit only; prod `:8787` health untouched
- `staff_ready=false` `human_commissioned=false` in RESULT

## Arm constraints (this run)

- Telegram incomplete → implement **infrastructure / config / engine reuse** that does **not** invent operational rules.
- Leave unknown business fields **NEEDS CONFIGURATION**.
- `STOP_FOR_OWNER` only for true missing business rules that would force invention to claim Uma eng proof complete — prefer shipping incomplete-config honesty over inventing terminals/tolerances.

## Exit

`EXIT:0` when tests green **and** RESULT stamped (even if terminal inventory still NEEDS CONFIGURATION, as long as honesty is proven).  
Commit **local pack slice only**. No push.  
Leave `staff_ready=false` and `human_commissioned=false`.

## Do not

- Message Matt / invent till figures / invent EDC terminal IDs / invent variance thresholds
- Mutate prod `:8787`
- Hardcode Devi
- Equate ESB payment totals to EDC settlement
- Port Alchemist soft gap as approved Wolf tolerance
- Dual `cursor-agent -p`
- Steal Recipe/Haikal/forensic/finance human waits
- Exit Report / Intelligence

## Stamp / arm context (Peaches)

- Status target: **ARMED_RUNNING** then eng DONE
- Arm: `cursor-agent -p --force --workspace /Users/wolfterminal/beta-os`
- Credit: Owner overrides soft credit veto for this pack
- Queue: after CE-CANCEL EXIT (slot free); parallel humans Recipe/Haikal OK

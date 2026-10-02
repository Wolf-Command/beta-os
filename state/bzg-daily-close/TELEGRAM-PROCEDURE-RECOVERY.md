# TELEGRAM PROCEDURE RECOVERY — BZG / Uma Blu Daily Close (Till + EDC)

**Pack:** BZG-DAILY-CLOSE-TILL-EDC-1  
**Recovered_at:** 2026-10-02T19:45:00+08:00 WITA  
**Status:** `TELEGRAM_SOURCE_INCOMPLETE` for raw Telegram Desktop chat history · **SECONDARY_AUTHORISED_SOURCE_OK** for Alchemist Telegram-bot `/nightly` procedure  
**no_matt_message:** true (intermediate discovery stamp)

## Verdict

| Source class | Result |
|---|---|
| Telegram Desktop postbox (Keepcoder) message history | **NOT RECOVERED** — proprietary `db_sqlite` (“unsupported file format”); `strings` yielded no operational SOP text |
| Telegram export / chat dump files | **NOT FOUND** after exhaustive search |
| Alchemist Telegram bot `/nightly` + `/eod` (authorised ops path staff used) | **RECOVERED** — live code + media evidence |
| Owner-authorised decisions / canon / Devi packs | **USED as secondary** (cited below) — do not pretend these are Telegram chat |

**Do not invent** terminal IDs, floats, tolerances, or financial rules beyond what is explicitly cited. Unknown → **NEEDS CONFIGURATION**.

---

## Everywhere searched

### Mac Studio (`36d8fa4b-2d58-4983-b227-e5bfa5495e78`)

| Path | Finding |
|---|---|
| `~/Library/Group Containers/6N38VWS5BX.ru.keepcoder.Telegram/appstore/account-694867054387081856/postbox/db/db_sqlite` (~96MB + WAL) | Present; **not** readable SQLite; strings filter for till/EDC/cashier/settlement/nightly → **no SOP text** |
| `~/Library/Containers/ru.keepcoder.Telegram/` | HTTP cache SQLite only (~2.3MB) — no chat SOP |
| `~/.openclaw/telegram/` | `update-offset-default.json` only |
| `~/.openclaw/workspace/alchemist/nightly_cmd.py` | **HIT** — full EOD close conversation (see §Operational requirements) |
| `~/.openclaw/workspace/alchemist/media/nightly/` | **HIT** — **404** photo files (`edc_*`, `pos_*`) proving live TG photo capture of EDC/POS |
| `~/.openclaw/workspace/alchemist/state/nightly-closers.json` | Learned closer names present (picker history) |
| `~/.openclaw/wolf-output/decisions.md` | **HIT** — 2026-09-17 Uma Daily Close pick; 2026-08-02 BZG cash-audit / till float |
| `~/.openclaw/memory`, `state/peaches-memory`, `workspace/memory` | No standalone closing SOP chat dump |
| `~/Documents/Wolf-Vault*`, `/Volumes/05-Wolf-Vault-Mirror` | STAFF-TELEGRAM-PROMPTS (generic); no till/EDC procedure body |
| `beta-os/state/build-factory/devi-uma-commission-pack.tgz` | Commission auth / phone message — **no** till/EDC step list |
| `beta-os/docs/canon/UMA-BLU-DAILY-CLOSE.md` | Current Wolf close honesty table (secondary) |
| `beta-os/.../WAVE2-01-UMA-DECLARED-CASH-EVIDENCE-RESULT.md` | Declared cash still null; settlement honesty |
| `beta-os/.../PROPOSED-UMA-VARIANCE-POLICY.md` | Thresholds **UNRESOLVED** / not loaded |
| Find `*telegram*export*`, chat dumps, ClickUp→TG bridges under Documents/Desktop/Downloads/beta-os | **No** closing SOP export found |
| Obsidian `WolfCommandSystem/WolfCommand` | No till/EDC close SOP note located this pass |

### Box

| Path | Finding |
|---|---|
| `/home/box/wolf-system`, `/home/box/workspace` | Owner order + production-line only at search time |
| Peaches TG learn artifacts / agent transcripts mentioning closing SOP | **No** recoverable TG transcript of closing SOP on box |

---

## Authorised procedure recovered (Alchemist Telegram `/nightly`)

**Source path:** `/Users/wolfterminal/.openclaw/workspace/alchemist/nightly_cmd.py`  
**Entry:** `/nightly`, `/eod`, menu `menu:nightly`  
**Default outlet (code):** `Uma Blu Cafe`  
**Sheet tab:** `Nightly Reconciliation`  
**Media dir:** `~/.openclaw/workspace/alchemist/media/nightly/` (404 files observed 2026-10-02)

### Flow (operational requirements preserved)

1. **Auth gate** — receiver allow-list (`is_receiver`); otherwise “Ask Devi to add you”.
2. **POS / till Z-report PHOTO mandatory** — OCR → `business_date`, `gross_sales`, `cash`, `card`, `qris`, optional `bills`/`covers`.
3. **Human confirm / fix** OCR before continue (no silent accept of OCR).
4. **Per EDC terminal SETTLEMENT slip PHOTO** — OCR → `bank` (acquirer label), `batch_total`, optional `txn_count`.
5. **Multi-EDC** — add another terminal or done; first-step skip = “no card today”; later skip = done.
6. **Columns written:** Date, Outlet, POS Gross, Cash, Card Total (sum of EDC batch totals), QRIS, EDC-1, EDC-2, EDC-3, Bank Settled *(blank)*, Variance *(blank)*, Status=`PENDING BANK`, Photos, Logged by (Telegram actor), Closed by (physical till closer).
7. **Closed by** picker distinct from Logged by — defaults in code `Devi`, `Saeful`, `Arya`, `Purnawan` + learned names file. **Wolf pack must not hardcode Devi**; use Assignment/Role/Scope (`ROLE-BZG-CLOSER`).
8. **Part 2** (bank settlement cross-reference) fills Bank Settled / Variance / Status — **not completed in Part 1**; status stays `PENDING BANK`.
9. **Photo mandatory** for POS and each claimed EDC; evidence uploaded (Drive link or local path).
10. **Back/re-shoot** flags Mr Wolf (training / theft-pattern) — does not delete a saved row (row only written after Closed by).

### Soft POS internal gap warn (Alchemist code — NOT Wolf policy)

`_pos_gap` in `nightly_cmd.py` uses soft warn when `|Gross − (Cash+Card+QRIS)| > max(2% of gross, Rp 5,000)`.  
**Owner order:** do **not** invent tolerances; variance requires review **without** tolerance.  
→ Treat Alchemist soft warn as **historical bot behaviour only**. **Do not** seed `venue_close_variance_policies` from it.  
**NEEDS CONFIGURATION / STOP_FOR_OWNER:** whether any soft OCR-warn remains UX-only vs zero-tolerance review gate (current Uma Daily Close already: live policy rows = 0 → any cash≠ESB → `VARIANCE_REQUIRES_POLICY`).

### Cash-audit related Owner decision (not Telegram chat; authorised)

**Source:** `~/.openclaw/wolf-output/decisions.md` · 2026-08-02 · PICK BZG cash-audit chain  
- Petty top-ups FROM till takings subtract from weekly deposit  
- **Rp 1,000,000 till float** constant and **EXCLUDED** from deposit equation  
- Card ≈ Mandiri settlement credits; QRIS ≈ BRI (net MDR)  
- Equation uses **Nightly Reconciliation.Cash**  
→ Float amount is Owner-confirmed in decisions.md. Still mark engine field for float handling as **config from this citation**, not invented. Bank Part 2 / settlement evidence remains separate from ESB payment lines.

### Alchemist outlet list (historical TG bot)

`OUTLETS` in `petty_cash.py` / `bzg_receive.py`:  
`Uma Blu Cafe`, `Blu Zone Restaurant`, `Underground Bar`, `Pool Bar`, `Rooftop Bar`, `Catering`, `Room Service`  
`ACTIVE_OUTLETS` = `["Uma Blu Cafe"]` only.  
**Owner order names** differ (e.g. Blu Zone Rainforest Restaurant & Bar, Merah Underground). Map via **canonical outlet registry** — do not hardcode seven strings; mismatches → **NEEDS CONFIGURATION**.

---

## Gaps vs current Uma Blu Daily Close (summary)

See `GAP-VS-UMA-DAILY-CLOSE.md` for full matrix. Headline:

| Alchemist TG `/nightly` | Current `venue_close` / Uma Daily Close |
|---|---|
| POS Z-report photo + OCR cash/card/qris/gross | ESB warehouse snapshot + declared cash evidence; **no** Z-report/EDC slip model |
| Per-terminal EDC settlement slip photos | **Missing** — settlement_api **UNAVAILABLE**; ESB cash = payment lines ≠ settlement |
| Card Total = Σ EDC batches | Not modelled per terminal |
| PENDING BANK Part 2 | Honest UNAVAILABLE; no fake bank match |
| Soft 2%/5k POS gap warn | Live variance policy rows = **0**; non-zero → VARIANCE_REQUIRES_POLICY (**keep**; do not port Alchemist soft tolerance as policy) |
| Uma Blu Cafe default only | Uma-scoped engine; need **one** BZG engine + outlet config for 7 |

---

## Explicit UNKNOWN / NEEDS CONFIGURATION

1. **Uma Blu physical EDC terminal inventory** (count, bank/acquirer labels, device IDs) — **NEEDS CONFIGURATION** (do not invent; Alchemist supports up to 3 named columns + “add another” but does not prove device registry).
2. **Variance absolute threshold** — UNRESOLVED (`PROPOSED-UMA-VARIANCE-POLICY.md`); live = 0 rows; Owner: review without invented tolerance.
3. **Settlement API / bank Part 2 automation** — **UNAVAILABLE** unless newly proved (not proved this recovery).
4. **Raw Telegram Desktop chat SOP narrative** (human prose instructions beyond bot code) — **TELEGRAM_SOURCE_INCOMPLETE**.
5. **Outlet display-name map** Owner list ↔ `org_outlet_registry` ↔ Alchemist OUTLETS — **NEEDS CONFIGURATION** where names diverge.
6. **Who holds ROLE-BZG-CLOSER seat for Uma** — Assignment/Role/Scope; closer seat historically empty in canon; **do not hardcode Devi**.

## Provenance index

Companion JSON: `TELEGRAM-PROCEDURE-RECOVERY.json`

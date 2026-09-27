# AUDIT — GGV Finance Mobile Nota Reuse — 2026-09-24

**Run:** `BF-ggv-finance-mobile-nota-20260924`  
**Workspace:** `/Users/wolfterminal/beta-os` · branch `build/wolf-command-rebuild` · soft head `f3ab8f7`  
**Prod:** :8787 PID 15975 sacred · Beta :8788 only  
**Recorded:** 2026-09-24 10:56 WITA  
**Auditor:** Peaches executor (Grok) on Mac Studio

## Verdict (one line)
**Partial reuse / mostly greenfield on Wolf GGV Finance surface.** Auth/RBAC/Evidence/Audit/Approvals/Wolf shell exist. No Wolf Vendor Master, no `ggv-finance` route, no finance.nota permissions. Telegram Alchemist nota is **external historical** — do not sync or retire in this pack.

## What exists (reuse)

| Asset | Path / fact | Reuse how |
|-------|-------------|-----------|
| AuthIdentity → Person | `scripts/core/identity.py` + `org_auth_identities` | EMAIL → Person binding; **no hard-code names in UI auth** |
| Request auth | `scripts/core/request_auth.py` | CF Access JWT → verified email → Person |
| RBAC | `scripts/core/rbac.py` + `org_permissions` | Add `finance.nota.*` / `vendor.*` / `evidence.create` codes; deny-by-default |
| Authority limits | `scripts/core/authority.py` | Keep payment/banking authority **separate** from operating nota perms |
| Evidence spine | `scripts/core/evidence.py` | Attach nota/PDF/photos as evidence; submit/read already coded |
| Audit | `scripts/core/audit.py` | Audit trail for create/edit/submit/dup decisions |
| Approvals | `scripts/core/approvals.py` | Optional later for Waiting Approval — only where model supports |
| SoD | `scripts/core/sod.py` | Person independence for approval paths (payment out of scope) |
| Wolf shell / GGV grammar | `scripts/core/wolf_shell.py` | GGV Finance slot is **EMPTY** (`href: None`); Amanda = `PERS-AMANDA` → `SPECIALIST_GGV` → `/ggv-ops-pack` |
| Persons | catalog | `PERS-MATT` (Matthew Goss), `PERS-AMANDA` (Amanda) present |
| Evidence permissions | catalog | `evidence.record.submit`, `evidence.record.read`, `evidence.requirement.manage` |
| BZG bills (different domain) | `dashboards/bzg-uma-blu-bills.html` | Pattern reference only — **not** GGV Vendor Master / Nota |
| Content upload / NAS | `scripts/core/nas_library.py`, content upload UX | Reuse **progress UX patterns** only — not content library as AP store |
| Global Wolf shell / responsive | existing shell tokens + responsive prove | Mobile-first chrome |

## What does NOT exist in Wolf (greenfield for this pack)

| Gap | Notes |
|-----|-------|
| `ggv-finance.html` / `/ggv/finance` (or equivalent) live route | Grammar marks Finance **EMPTY** — intentional until this pack |
| Wolf **Vendor Master** | No `*vendor*` core module / dashboard in beta-os |
| `finance.nota.read/create/edit` permissions | Not in `org_permissions` |
| `vendor.read/create/edit` permissions | Not in `org_permissions` |
| Dedicated `evidence.create` code (may alias submit) | Spec asks conceptual split; map to existing evidence.submit or add code |
| Mobile Nota upload → OCR extract → vendor match → submit workflow | Greenfield UI + APIs on Beta |
| Canonical GGV AP/nota record model in Wolf | Must be bounded + Zayen-compatible; no competing ledger |
| PR #151 nota remnants in beta-os docs/state | **Not found** under named PR#151 artifacts (search 2026-09-24) |

## External / historical (reference only — do NOT operate from)

| Asset | Location | Rule |
|-------|----------|------|
| Telegram Alchemist nota verify | `~/.openclaw/workspace/alchemist/nota_verify.py` (+ `bot.py`, `db.py`, `supplier_master.py`) | **BZG Uma Blu procurement** via TG. Historical. Do **not** sync Wolf↔TG. Do **not** create new TG vendor/nota from this pack. Do **not** claim TG retired until Matt+Amanda human commissioning both PASS. |
| Informal Xero vendor map | `~/.openclaw/workspace/memory/xero-vendor-map.json` | Not Wolf Vendor Master. May inform seed **candidates** only with human confirmation — never silent import as verified bank/master. |
| Telegram keepalive / bot creds | `~/.openclaw/` | Out of scope. Engineering must make Wolf work **without** Telegram. |

## Integration boundary (Zayen)

- This pack builds **bounded AP / evidence intake** for GGV inside Wolf.
- **Zayen full Finance** (reconciliation, cash, P&L, AP ageing, payment execute) is **reserved later**.
- Records created here must carry: Wolf record ID, vendor ID, source attachment, creator, timestamp, confirmed amount/date, workflow state, history, audit.
- States only where model supports: Needs Review, Ready, Waiting Approval, Approved, Paid — Claimed, Payment Verified.
- **NOTA ENTERED ≠ APPROVED ≠ PAID ≠ PAYMENT VERIFIED.**
- No bank write. No payment execute. No invented monetary limits.
- BANK DETAILS OBSERVED ≠ VERIFIED — capture as source evidence only.

## Permission split (must implement)

**Operating (this pack):** `finance.nota.read|create|edit`, `vendor.read|create|edit`, `evidence.create` (or map to evidence.record.submit)  
**NOT this pack / higher risk:** `payment.approve`, `payment.execute`, `vendor.bank.change`, `finance.policy.admin`

Authorised staff via EMAIL → AuthIdentity → Person → Role → Assignment → Scope → Permission. UI must not hard-code "Matt"/"Amanda".

## Telegram retirement gate

- Build Wolf to function **without** Telegram.
- Do **not** retire TG in code as end-state claim.
- Do **not** sync Wolf→TG or invent new TG vendor/nota records from this pack.
- Historical TG evidence stays historical.
- Retire TG **only after** human commissioning both Matt + Amanda accept (Peaches My Commissioning cards — after engineering pass).

## Cheap search notes

- Dashboards: `ggv-ops-pack`, profitability, intercompany, social, strategy — **no** finance/nota page.
- `docs/RULE*Finance*`, `*Vendor*`, `*Nota*` — none in beta-os RULE set.
- Soft head `f3ab8f7` uncommitted work **preserved** this audit.

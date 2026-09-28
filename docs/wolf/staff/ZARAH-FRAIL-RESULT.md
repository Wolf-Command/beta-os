# Zarah and Frail — Creative Director — 28 Sep 2026

Owner directive (Matthew, 28 Sep 2026 13:34 WITA). Extends the staff registry. Not a new system. Beta `:8788` only. Production `:8787` stayed pid 15975. No push. No Cloudflare edit. The Owner had already put both emails on the Beta Access include list.

STAFF READY is false. HUMAN COMMISSIONED is false. Commissioning stays PENDING. Neither person has been signed in. Pronouns were not recorded. The pages greet them by name.

## What already existed

Nothing. No Person row and no AuthIdentity row matched `zarah.lestrange@gmail.com`, `frail.bongat@icloud.com`, or the names Zarah, Frail, Lestrange, or Bongat. The seats below were created. They were not a second copy of an existing person.

## Chain

AuthIdentity → Person → Role → Position → Assignment → Scope → Permission → Audience.

The role is the existing `ROLE-GGV-CREATIVE-DIRECTOR` (Creative Director). Haikal holds `POS-GGV-CREATIVE-DIRECTOR-1` / `ASG-HAIKAL-CD-1`. Misa holds `POS-GGV-CREATIVE-DIRECTOR-2` / `ASG-MISA-CD-1`. No role was added. No person-named role was added. The role's grants were not changed.

| | Zarah | Frail |
| --- | --- | --- |
| Person | `PERS-ZARAH` | `PERS-FRAIL` |
| AuthIdentity | `AUTH-ZARAH-EMAIL` | `AUTH-FRAIL-EMAIL` |
| Email | `zarah.lestrange@gmail.com` | `frail.bongat@icloud.com` |
| Role | `ROLE-GGV-CREATIVE-DIRECTOR` | `ROLE-GGV-CREATIVE-DIRECTOR` |
| Position | `POS-GGV-CREATIVE-DIRECTOR-3` | `POS-GGV-CREATIVE-DIRECTOR-4` |
| Assignment | `ASG-ZARAH-CD-1` primary ACTIVE | `ASG-FRAIL-CD-1` primary ACTIVE |
| Audience | `SPECIALIST_CONTENT` | `SPECIALIST_CONTENT` |
| Landing | `/content-2.0` | `/content-2.0` |

## Scopes

Same five scopes as Haikal's active Creative Director assignment:

- `SCOPE-CRM-HABITAT-LEAD`
- `SCOPE-GGV-CONTENT`
- `SCOPE-GGV-CONTENT-LIBRARY`
- `SCOPE-GGV-HABITAT-LEAD`
- `SCOPE-WOLF-CONTENT-ALL-BRANDS`

`SCOPE-WOLF-CONTENT-ALL-BRANDS` is the content-brand grant already on that role's seats. It covers atrium, goss, habitat, rainforest, selo, theone, tropik, and umablu. A brand token outside that set (`not-a-brand`) is denied. No extra brand was added.

## Grants

The role already allows these codes. Nothing was added:

- `approval.decide`
- `approval.request`
- `content.asset.upload`
- `content.habitat.approve`
- `content.plan.edit`
- `content.plan.read`
- `content.production.update`
- `evidence.record.submit`
- `work.assign`
- `work.read`
- `work.update`

Still denied, same as Haikal: `content.habitat.publish.request`, `content.plan.approve`, finance nota read and create, payment approve and execute, bank change, organisation role and person read, `progress.read`, hotel day operator, Uma close, `core.operator`, governance authorise.

Publishing stays on the existing Publish Gate. `GET /api/planner/publish-gate?id=1` returns the same allowed, stage, and reason for Zarah, Frail, and Haikal.

## Test matrix

`scripts/tests/test_zarah_frail_cd_20260928.py` — SUMMARY pass=150 fail=0.

| Check | Result |
| --- | --- |
| Login identity, both emails, mixed case and uppercase | Pass. Resolves to the one person |
| `/` → `/content-2.0` | Pass. 302, HTML, not JSON |
| Content page | Pass. 200, Content Engine |
| Library | Pass. Brand registry 200. `GET /api/assets?brand=habitat` 200 |
| Authorised brands | Pass. Same eight as Haikal |
| Unknown brand | Pass. `not-a-brand` is 403 JSON |
| Upload | Pass. Empty preview is 400 `brand required`. No file was written. Atrium Finance Officer stays 403 |
| Download | Pass. Missing asset is 404 after the content gate. Atrium Finance Officer stays 403 |
| My Work | Pass. Page 200. API experience `creative_director`, label Creative Director, greeting `Hello, Zarah` / `Hello, Frail` |
| Assign and review | Pass. `work.assign`, `content.plan.edit`, `content.habitat.approve`, `approval.decide` |
| Publish Gate | Pass. Same response as Haikal. `content.habitat.publish.request` stays denied |
| Finance, HR, Owner, Admin pages | Pass. HTML Access denied, with the email and a link back to `/content-2.0` |
| Finance, HR, Admin APIs | Pass. JSON 403 |
| Uma Blu page | Pass. 403, same as Haikal |
| Succession | Pass. Ending Zarah's assignment removes her access and keeps the row. Frail keeps access. A replacement on the same role and the same scopes gets the same rights and is denied finance |
| Second apply | Pass. Still one person each. Scope rows do not double |
| Logout | Pass. `/signout` is 302 to the Beta Access logout URL |
| Flags | Pass. `staff_ready` false. `human_commissioned` false |

Kept green alongside this file:

| suite | result |
| --- | --- |
| `test_role_routing_20260928.py` | SUMMARY pass=84 fail=0 |
| `test_staff_access_20260928.py` | SUMMARY pass=274 fail=0 |
| `test_ggv_finance_invoice_20260928.py` | PASS=92 FAIL=0 |
| `test_ggv_finance_mobile_nota.py` | PASS=138 FAIL=0 |
| `test_ggv_finance_nota_storage_accountant.py` | PASS=100 FAIL=0 |

## Beta

Beta was restarted from pid 68812 to pid 71613 (`state/build-factory/detach.py` then `scripts/serve_beta.py`). `GET /api/health` is HTTP 200. Unsigned `GET /` is HTTP 403 HTML. Production `:8787` stayed pid 15975. Authority limits stay 0. SoD constraints stay 0.

RESULT: PASS

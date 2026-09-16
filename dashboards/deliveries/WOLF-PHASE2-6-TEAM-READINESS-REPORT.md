# WOLF Phase 2.6 — Team Readiness
**For:** Peaches only  
**When:** 2026-09-15 16:27:03 WITA  
**Lane:** Beta OS `/Users/wolfterminal/beta-os/` on **:8788 ONLY**  
**URL:** https://beta.wolfcommand.net/content-2.0.html  
**Machine:** Wolfs-Mac-Studio.local (`36d8fa4b-2d58-4983-b227-e5bfa5495e78`)

---

## Executive result: **PASS**

Content Engine 2.0 is ready for wider team testing on Beta, based on Haikal real UX + footage feedback. Habitat operational plan **#9** reused (not regenerated). Automated acceptance **42/42**.

---

## Hard confirmations

| Guard | Status |
|---|---|
| NO :8787 touch | **CONFIRMED** (PID **32884** unchanged before→after) |
| NO Metricool write | **CONFIRMED** |
| NO publish | **CONFIRMED** (`published: false` on approve) |
| NO live multi-model routing | **CONFIRMED** (WI shell says not connected) |
| NO semantic / CV / embeddings | **CONFIRMED** |
| NO test pollution of ops | **CONFIRMED** (`data_lane=test` filtered; overlap=0) |
| NO wolf-system edits | **CONFIRMED** |

---

## §1 Permissions (supersedes 2.5A)

| Subject | Grants |
|---|---|
| Matt `mrwolf@wolfcommand.net` | create + edit + approve + view + production + upload + WI |
| Amanda `amanda@wolfcommand.net` | same as Matt |
| Haikal `haikalqilbari123@gmail.com` | edit + production + upload + WI + view; **NO create, NO approve** |
| Misa `mlsary111@gmail.com` | same as Haikal |

Server-side enforce via `_require_permission`.  
Edit of approved/working plan by crew → save edit revision, **preserve previous approved**, mark **CHANGES PENDING REVIEW** (not silent APPROVED).  
States: **APPROVED → CHANGES PENDING REVIEW → APPROVED**.  
Matt/Amanda UI: **VIEW CHANGES / APPROVE CHANGES / REQUEST REVISION**.

---

## §2–4 Content briefs

**Posts:** POST TITLE, POST TYPE (Reel·30sec / Carousel·6 slides / Static), PILLAR, CONTENT BREAKDOWN, CAPTION DIRECTION, CTA, HASHTAGS, RECOMMENDED SHOT LIST, STATUS, ASSIGNEE, INSPIRATION/EXAMPLES.  
Goal/Theme/Concept/Hook **not forced** on team brief (still available internally).  

**Stories:** STORY TITLE, GOAL/PURPOSE, STORY BREAKDOWN, CTA (NONE/LINK STICKER/POLL/QUESTION/QUIZ/REACTION/DM/OTHER), evergreen bool (no forced calendar date).

---

## §5 Content modal

Right drawer replaced with **centered modal**: dimmed backdrop, scrollable body, comfortable width (~720px), clear Close/Cancel, Save. Full-screen only on small screens.

---

## §6 Dashboard

Separate **Posts progress** and **Stories progress** (e.g. `0/3` and `0/14`) from Habitat plan #9 targets.

---

## §7 Status visuals

NOT STARTED · NEEDS FILMING · READY · IN PRODUCTION · EDITING · READY FOR REVIEW · COMPLETE — color + text + dot marker, high-contrast badges.

---

## §8 Default assignee

Brand-level `brands.default_assignee` (Habitat → Haikal). Inherited on empty assignee; human override preserved. Not frontend-only.

---

## §9 Brand theming

Restrained: logo mark + primary + accent (+ neutral). One common font (Inter/system). Same layout; accents/logo only via CSS vars from `/api/brands`.

---

## §10–15 Library

Large search; filters in user language: Brand, Video/Photo, RAW/EDIT/FINAL, Ready/Checking/Failed, Shoot Date, Subject, Location.  
Asset cards: thumb, brand badge, canonical name, original secondary, media type, shoot date, subject, detail, readiness.  
Click → preview modal (play video if compatible / large photo). **No FS paths.**  
Hover/preview: muted video when ready; otherwise honest “preview unavailable” (no fake proxy).  
Download single + multi-select ZIP (permissioned; max 40).  
Readiness: READY TO USE / CHECKING / FAILED (+ note).

---

## §16–23 Upload

Required: Brand*, Stage*, Media Type*, Shoot Date*, Subject*, Default Detail* (≥1 slug tokens → `detail_tags_json`). Location optional.  
**Content Plan/Card removed from normal Upload UI** (nullable backend kept). One brand per batch.  
Clear active wizard queue after READY/FAILED terminal; Recent Uploads kept; Library never deleted.  
Duplicate protection via hash/size/original/canonical — **409 warn**, `force=1` to proceed.  
Progress per-file + overall; safe parallel concurrency=2 (documented).  
Honest NAS: `nas_received` never true unless proven.

---

## §24–26 Wolf Intelligence

Chat UI shell: transcript, compose box, send, clear/new. Context: Brand + content item.  
Quick actions: REFINE / HOOK / FOOTAGE / CTA / SHORTEN CAPTION / ANOTHER IDEA / BRAND FIT / SIMILAR / PERFORMED WELL / INSPIRATION.  
Unavailable = says not connected. No fabricate. WI does **not** silently edit plan (`can_apply_to_plan: false`).

---

## §28 Test

Used existing **Habitat operational plan #9**. Fixtures use `data_lane=test`. No ops pollution.  
Suite: `scripts/tests/test_phase2_6_team_readiness.py` → **PASS=42 FAIL=0**  
Log: `/tmp/WOLF-PHASE2-6-TEST-OUT.txt`

---

## §29 Out of scope (not built)

semantic matching, CV, embeddings, READY/PARTIAL/FILM auto, live trends, Learning Library, multi-model routing, Metricool write, publish, Remotion, **:8787**.

---

## Files changed

| Path | Role |
|---|---|
| `scripts/migrations/migrate_phase2_6_team_readiness.py` | **NEW** schema + permissions |
| `scripts/migrations/004_phase2_6_team_readiness.sql` | **NEW** notes |
| `scripts/phase26_team.py` | **NEW** helpers |
| `scripts/serve_beta.py` | routes, UX briefs, library, WI, media, ZIP, review APIs |
| `scripts/skills/__init__.py` | pending review + approve/request + draft fields |
| `scripts/smart_upload.py` | detail required, hash, tags, duplicate warn |
| `dashboards/content-2.0.html` | modal, briefs, dashboard, library, upload, WI, review UI |
| `scripts/tests/test_phase2_6_team_readiness.py` | **NEW** acceptance |

**Backups:** `archive/baks/*phase2-6-20260915-161506` · `catalog/backups/content_library.sqlite.bak-phase2-6-20260915-161506`

---

## Serving status

- **:8788** listening — OK (restarted after Phase 2.6)
- **:8787** PID **32884** untouched — OK
- Health: `{"ok": true, "root": "beta-os", "planner": "sqlite"}`
- Habitat plan #9: `Human_Approved` / review_state `APPROVED`

---

## Known gaps / honest limitations

- Cloudflare Access JWT still not wired (dev `X-Wolf-Subject` only).
- WI live generation not connected (shell only).
- Hover lightweight proxy not built — UI documents limitation when preview file missing.
- ZIP requires readable files under Beta `library_v2` (no NAS ingest).
- Safe upload parallel = 2 (not unbounded).
- Existing Habitat card bodies still carry legacy hook/goal internally; team modal shows Phase 2.6 primary fields.
- Multi-brand theming beyond Habitat is schema-ready; only Habitat seeded.

---

## Haikal retest checklist

1. Open https://beta.wolfcommand.net/content-2.0.html as Haikal (subject selector).
2. Confirm nav: Dashboard · Content Plan · Library · Upload · Wolf Intelligence (unchanged order).
3. Dashboard shows separate Posts vs Stories progress for Habitat.
4. Open Content Plan → Habitat fortnight #9 → open a Post → centered modal with primary fields only (no forced Goal/Theme/Concept/Hook).
5. Edit caption/assignee → Save → status shows **CHANGES PENDING REVIEW** (not silent APPROVED). Haikal has no Approve.
6. Switch to Matt → VIEW CHANGES / APPROVE CHANGES / REQUEST REVISION work; after approve → **APPROVED**.
7. Stories: evergreen checkbox; CTA dropdown; simpler fields.
8. Library: large search + Brand/Video-Photo/Stage/Readiness/Shoot/Subject/Location filters; card shows canonical + original; no paths; preview modal; multi ZIP.
9. Upload: Detail required; no Content Plan/Card fields; batch one brand; after finish wizard clears; Recent Uploads remain; duplicate warn if re-upload same file.
10. Wolf Intelligence: quick actions + chat; replies say not connected; does not edit plan.
11. Confirm cannot Build Next / Approve as Haikal.

---

## STOP

Phase 2.6 Team Readiness complete. URL for Peaches only: https://beta.wolfcommand.net/content-2.0.html

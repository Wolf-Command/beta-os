# ADDENDUM — Content Engine Staff Shell Cleanup — 2026-09-24

**Owner directive:** CONTENT ENGINE — STAFF SHELL CLEANUP (2026-09-24 ~17:30 WITA).  
**Fold into:** `BF-content-engine-haikal-fail-repair-20260924` (active Cursor pack — **do not kill / do not launch new redesign pack**).  
**Gate label:** `CONTENT ENGINE READY FOR HAIKAL RETEST` only after this ADDENDUM is implemented on Beta `:8788` **and** Peaches verify.  
**staff_ready:** always **false** in this fold.  
**Armed:** 2026-09-24 ~17:35 WITA · Executor local docs only (Cursor 45807 left running).

## Target staff header

```
☰ | [BRAND ▼] | CONTENT ENGINE | Content Plan | Library | Upload
                                              right: Hi, {first_name} | profile
```

## Auth (unchanged chain)

`Person → Assignment → Role → Scope → Permission → Audience`

Haikal access via **Creative Director Assignment** (`ASG-HAIKAL-CD-1` → `POS-GGV-CREATIVE-DIRECTOR-1` → `ROLE-GGV-CREATIVE-DIRECTOR`) — not person-name gates. See `docs/deliveries/NOTE-Haikal-Creative-Director-Assignment-2026-09-24.md`.

## REMOVE from normal staff view

Boards · Wolf · Up · Back · Home · DEV IDENTITY · SPECIALIST_CONTENT · ROLE-CONTENT · raw email · NAS technical status language · internal debug.

Keep on **System / Admin** surfaces if still needed. **Do not weaken server-side permissions** (hidden UI ≠ security).

## Brand selector

- Source: **Brand Registry** + Assignment/Scope (not hard-coded CE copies).
- Eight required brands: Atrium, Uma Blu, Selo Group, Habitat, Tropik, The One, Blu Zone Rainforest Resto, Goss Group.
- **All Brands** when multi-brand scope authorises.

## Wolf Intelligence

Hide from **primary CE nav** until useful (connect-or-hide already in pack SPEC §9 — this ADDENDUM prefers **hide** for staff shell until ready).

## Upload UX

- Remove permanent 7-stage pipeline chrome from the **main** page.
- Simple truthful status **during** upload only.
- Failures: **Retry** (preserve successes).
- No healthy-NAS green banner.

## MEDIA TYPE vs CONTENT TYPE (do not invent)

**Search result (2026-09-24):**

| Layer | Found? | Path / note |
| --- | --- | --- |
| Canonical media-type tuple | **YES** | `scripts/wolf_naming.py` → `MEDIA_TYPES = ("video", "audio", "image", "broll", "graphic")`; mirrored `ASSET_TYPES` in `scripts/serve_beta.py` |
| Separate CONTENT TYPE enum (B-roll / Testimonial / Property / Food / People / Event / Lifestyle) | **NO fixed canon** | Upload uses freeform **subject** + **detail** slug tokens (`detail_valid` / `parse_detail_tags` via phase2.6); DB columns `assets.subject`, `assets.detail`, `assets.detail_tags_json` |
| Historical conflation | `broll` lives inside MEDIA/ASSET types today | Owner wants MEDIA TYPE (Photo/Video/Audio/Graphic) **separate** from CONTENT TYPE |

**Implementation rule for Cursor:** do **not** hard-code Owner's CONTENT TYPE list if extending — prefer wire to existing subject/detail + naming canon; if a discrete CONTENT TYPE facet is required, add as documented canon extension (not silent UI invent). MEDIA TYPE staff labels may map image→Photo, video→Video, audio→Audio, graphic→Graphic; treat `broll` as content-class debt vs media-kind.

## Library staff view

- Thumb first · human title · small **Brand · Media type · Date**
- Technical names in **Preview** only
- Preserve multi-select / ZIP / download / preview PASS
- Blank thumbs = still open repair debt (not normal)

## Staff design test

Professional CMS — **not** an engineering panel.

## Gate / locks

- Next human label only after Peaches verify + shell criteria: **CONTENT ENGINE READY FOR HAIKAL RETEST**
- `staff_ready=false` locked
- If Cursor **EXIT** before implementing this ADDENDUM: Peaches verify **MUST FAIL** shell criteria → surgical Beta fix or bounded same-run follow-up — **not** a new breadth pack  
  See `docs/deliveries/NOTE-CE-Staff-Shell-Cleanup-Fold-Into-Active-Pack-2026-09-24.md`

## Related

- RULE: `docs/RULE-Content-Engine-Haikal-Fail-Repair-2026-09-24.md` (ADDENDUM pointer)
- SPEC: `docs/deliveries/SPEC-Content-Engine-Haikal-Fail-Repair-2026-09-24.md` (ADDENDUM pointer)
- Commissioning: `state/commissioning/CONTENT-ENGINE-HAIKAL-2026-09-24.md`
- GATE: `state/build-factory/GATE-content-engine-haikal-fail-repair-20260924.json`
- CR: `state/completion-register/content-engine-haikal-fail-repair-20260924.json`

# Habitat Full Authorised Knowledge Sweep — 17 Sep 2026

**Correction to:** `HABITAT-BRAND-INTELLIGENCE-DISCOVERY-2026-09-17.md`  
**Principle:** SEARCH → RETRIEVE → COMPARE → CLASSIFY → CONFLICT → ask human only if necessary.  
**Mutations:** none · **Commissioning:** undisturbed · **Metricool writes:** none  

## Sources searched

| Class | What |
|---|---|
| Wolf Beta | `catalog/content_library.sqlite` (brands, org_*, memory_items, plans, performance, external ids), docs/canon, docs/deliveries, Content Machine |
| Legacy Wolf | `wolf-system` brand-strategy, design-bundle, style-profiles, content-studio (READ) |
| Obsidian vault | `/Users/wolfterminal/WolfCommandSystem/.../Habitat-Villas/Habitat-Brand.md`, `Habitat-Strategy.md` |
| NAS Brand-Assets | `/Volumes/01-Media-Library/Brand-Assets/GGV/Habitat/` (README, fonts, logos, palettes, style-guide PDF) |
| Google Drive | Connector search — brand guide PDF, brand cards, blog template, content plans |
| Notion | Search — Habitat task/content pages (production tasks; not brand bible) |
| Metricool settings | Prior mission — blogId 6260634 / handles (identity cross-check) |

## Sources known / partially inaccessible

| Source | Status |
|---|---|
| Canva kit `kAHLZuPxcnE` (cited in design-bundle) | **INACCESSIBLE** this run (no Canva connector used) |
| Full visual “feed grid inspiration” imagery inside PDF | PDF is **1 page** mostly visual; text extract limited to palette+Manrope+sub-brands |
| Client legal contracts / Keen Eye agreements | Not found in authorised search this pass |
| Model-release / usage-rights ledger | Not found |

## Grok-accessible Habitat sources (with provenance)

| Source | Authority |
|---|---|
| NAS `style-guide/Habitat_brand_guide.pdf` (+ Drive twin `Habitat_brand_guide.pdf`) | CLIENT-SUPPLIED / APPROVED SOURCE kit (visual identity sheet) |
| NAS `README.md` (2026-05-18) | OPERATIONAL SOURCE (asset pack index) |
| Obsidian `Habitat-Brand.md` (updated 2026-06-22 from brand-config) | OPERATIONAL / HISTORICAL compiled brand knowledge |
| Obsidian / wolf `Habitat-Strategy.md` | OPERATIONAL (kit-based, honesty: not finished-validated) |
| Drive `Wolf-Command-Brand-Cards-for-Design.md` | OPERATIONAL (vault specs for design) |
| Drive `Habitat Blog Template` | OPERATIONAL |
| Drive Habitat content plan Aug–Sep 2026 | OPERATIONAL / HISTORICAL campaign |
| Beta `memory_items` imported from Obsidian | CANONICAL-in-Wolf only where APPROVED; incomplete vs vault |
| Beta `brands.theme_json` Inter font | OPERATIONAL UI chrome (not brand kit) |

**Grok inference alone is not listed as evidence.**

---

## Brand guidelines

**BRAND GUIDELINES FOUND: YES**

| Field | Value |
|---|---|
| Primary path | `/Volumes/01-Media-Library/Brand-Assets/GGV/Habitat/style-guide/Habitat_brand_guide.pdf` |
| Also | Google Drive file `Habitat_brand_guide.pdf` (id `1s5NfhJTI6rxj1uzmtrskdQAnEruP3NLR`) |
| Type | CLIENT-SUPPLIED visual identity sheet (palette, Manrope roles, Garden/Vibe naming, feed grid inspiration imagery) |
| Date/version | File mtime ~2026-06-02 NAS; Drive created ~2026-06-16 — **version label unknown** |
| Extractable text | Colours #79755B / #EAE6D7 / #A6A28B / #FFFFFF / #232224; Brand font **Manrope** (Bold/Medium/Regular); Habitat Villas / Garden / Vibe |

Richer prose (pillars, tone bans, logo rules) lives in **Obsidian Habitat-Brand.md** compiled from brand-config + kit — treat as OPERATIONAL SOURCE, not a second “official PDF chapter.”

### Supported facts from guidelines + aligned kit docs

- Positioning / essence: considered living, quiet luxury, design-literate restraint (Habitat-Brand.md)  
- Voice: property-portfolio polish; architectural journal; ban luxury/stunning/don’t-miss-out  
- Typography: **Manrope** (ExtraBold/SemiBold/Bold/Medium roles)  
- Colours: as palette above  
- Logos: NAS logos paths + placement defaults  
- Visual: architectural detail, golden hour, no handheld wobble / trending audio  
- Pillars: five listed in Habitat-Brand.md  
- Products: Forest / Garden / Vibe inventory narrative in Habitat-Brand.md  
- Audience: investor / villa buyer emphasis in Drive content plan + blog template target audience fields  

---

## Manrope vs Inter — RESOLVED without human ask

| Claim | Source | Authority |
|---|---|---|
| Brand typeface = **Manrope** | Brand guide PDF, NAS README, Habitat-Brand.md, Habitat-Strategy, Drive brand cards, blog template, fonts zip | APPROVED / CLIENT kit |
| UI chrome font = **Inter** | Beta `phase26_team.py` / migration note: “shared Inter/system font — do not swap typefaces in UI”; `brands.theme_json` | OPERATIONAL UI |

**Resolution:** Manrope = Habitat **brand identity**. Inter = **shared Wolf Content Machine UI** chrome, deliberately not brand substitution. Not a brand-identity conflict requiring Matt — a **scope** distinction (marketing assets vs app chrome). Optional later: `theme_json.font` field should be labelled `ui_font` vs `brand_font` to stop false conflicts.

---

## Category maturity (FOUND vs CANONICAL-IN-WOLF)

| Category | Information exists | Canonical in Wolf |
|---|---|---|
| Brand identity | FOUND | PARTIAL (`org_brands`/`brands` + some APPROVED memory) |
| Brand voice | FOUND | PARTIAL (3 APPROVED RULEs; full vault richer) |
| Audience | FOUND (plans/templates) | NOT YET CANONICAL |
| Visual identity | FOUND | PARTIAL (colours APPROVED; Manrope APPROVED; Inter mis-scoped in theme_json) |
| Products/offers | FOUND | PARTIAL (FACTs APPROVED; pricing absent) |
| Content pillars | FOUND (vault) | NOT YET CANONICAL (memory still PROPOSED OBSERVATION) |
| Factual claims | FOUND | PARTIAL (inventory FACTs APPROVED; legal PT PMA still CLAIM from marketing) |
| Asset rights | NOT FOUND as rights records | ABSENT (files ≠ rights) |

## Conflicts found

1. **Manrope vs Inter** — resolved (brand vs UI)  
2. **Pillars APPROVED in vault prose vs PROPOSED in memory_items** — promotion gap, not content disagreement  
3. **Nindy listed as content lead in Habitat-Brand.md vs current roster (Misa/Haikal)** — HISTORICAL team field stale  
4. **Habitat-Brand “Luxury villa” type vs tone ban on “luxury”** — vocabulary tension inside same vault file  
5. **Uppercase Manrope headlines (strategy) vs lowercase-only (grid/brand cards)** — unresolved style detail; needs one authority pick later  

## Information FOUND but not canonical in Wolf

- Full Habitat-Brand.md / Strategy vault  
- NAS + Drive brand guide PDF  
- Drive brand cards + blog template + Aug–Sep content playbook  
- Design-bundle HTML cards  
- Canva kit id (referenced, not opened)  

## Truly HUMAN-HELD after search (why Wolf cannot answer)

| Gap | Why |
|---|---|
| Live unit availability / price this week | Vault FACTs dated; no live inventory feed found |
| Scarcity / ROI narrative unlocks | Policy only in Matthew’s head / not in searched docs |
| Model release / guest consent for specific faces | No rights ledger found |
| Keen Eye commercial terms / commission detail | Contract not found in authorised stores this pass |
| Which uppercase vs lowercase headline rule wins | Two OPERATIONAL sources disagree; no single newer official decree found |
| Canva kit pixel truth vs PDF | Canva inaccessible this run |

## Previous discovery corrections

| Earlier claim | Correction |
|---|---|
| Brand voice ABSENT/thin | **FOUND** in vault + kit + Drive |
| Visual ABSENT/thin | **FOUND** (PDF + NAS + logos) |
| Pillars only PROPOSED / weak | **FOUND** in Habitat-Brand.md; Wolf memory not yet promoted |
| Manrope vs Inter needs human | **RESOLVED** by source authority (brand vs UI) |
| Audience ABSENT | **FOUND** in Drive content plan / blog template (not yet Wolf-canonical) |
| Brand guidelines absent | **FOUND** on NAS + Drive |

## Future Wolf behaviour

Should search all authorised sources before asking: **YES**.

Current architecture: **PARTIAL** — connectors/files/NAS/vault exist but no single orchestration that always runs Search→Rank→Conflict before human ask.

Missing capability (one): **authorised multi-source knowledge resolve step** (Entity/Brand scoped) that returns provenance + conflicts — software skill/orchestrator, **not** a new agent.

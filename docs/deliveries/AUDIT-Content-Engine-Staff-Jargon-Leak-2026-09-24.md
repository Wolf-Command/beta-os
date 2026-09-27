# AUDIT — Content Engine Staff Jargon Leak — 2026-09-24

**Scope:** Staff-facing Beta Content Engine routes/surfaces only (`/content-2.0`, shared shell/nav used by that desk).  
**Out of scope:** Owner/System/Progress-only dashboards (AMG/BZG/GGV ops packs, Progress, empire packs) — leaks there are not this pack unless shared into Content.  
**Method:** Cheap deterministic `rg`-class pattern scan. No speculative breadth.  
**Recorded:** 2026-09-24 09:18 WITA  
**staff_ready:** false

## Patterns searched
`Operator depth` | `operator_depth` | `operator-depth` | `proven=` | `ready=` | `staff_ready=` / `staff_ready` | `human fake` | `No Haikal` | `NAS destroy` | `CR-` | `AU-` | `capability maturity` | `connective` | `ENGINEERING` | `SPECIFIED` | `Needs-You` / `Needs You` | `Decision Memory` | `AKR` | `full_tree_indexed` | invent-PROVEN slogans | `Haikal human`

## Staff route under audit
| Route | File | Role |
|-------|------|------|
| `/content-2.0` (alias `/content-2.0.html`) | `dashboards/content-2.0.html` | **Primary Haikal Content Engine desk** |
| Shared sidenav | `dashboards/assets/sidenav.js` | Global shell injected / shared |
| Shared shell CSS | `dashboards/assets/wolf-shell.css` | Visual shell |
| Tokens | `dashboards/wolf-tokens.css` | Design tokens (comment-only hit) |
| Shell IA (server) | `scripts/core/wolf_shell.py` | Nav/honesty source for shell |

No separate `brands-*` staff HTML found; brand peers redirect into `content-2.0` via `CONTENT_BRAND_REDIRECTS` in `wolf_shell.py`. Atlas Owner paths not staff Content.

## Top findings (prefer shared shell/nav/component fixes)

### P0 — `dashboards/content-2.0.html` (staff-visible chrome)
1. **Intelligence grammar strip** exposes engineering empties: `Decision Memory · EMPTY`, `AKR · EMPTY` (lines ~448–449). **Remove from staff Content surface** (Owner design: WI assist without AKR/DM exposure).
2. **LIBRARY** embeds **Operator depth** + **NAS index** engineering panels with slogans: `No Haikal human fake`, `No NAS destroy`, `proven=false · ready=false · staff_ready=false`, `Needs-You`, `CR … stays OPEN`, `full_tree_indexed=false`, `no invent PROVEN/READY` (~542–550, ~1460–1669). **Hide/relocate off staff Library** (Owner/Progress or API-only). Library must be search → thumbnail grid → select/download.
3. Dynamic banners after operator actions repeat `staff_ready=false`, `NAS destroy`, `Needs-You` — staff-facing.
4. Upload/NAS banner honesty is partly good (no fake NAS) but wording still eng-heavy in places (“nas_received only after verify”).

### P1 — Shared shell suspects
1. `dashboards/assets/sidenav.js` — staff nav includes **Needs You** title/key; comment “No invent PROVEN/READY” (dev comment OK if not rendered). For Haikal primary desk, Needs You must not dominate the four staff tabs.
2. `scripts/core/wolf_shell.py` — grammar entries `Decision Memory` / `AKR` EMPTY; `Needs You` in audience nav; honesty `staff_ready` / `proven` flags. **Fix preference:** staff Content page-type / audience `SPECIALIST_CONTENT` omits AKR/DM grammar + ops-depth chrome; keep honesty server-side.
3. `dashboards/wolf-tokens.css` — comment-only PROVEN/READY note (non-rendered; low).

### Not in this pack
- AMG/BZG/GGV/CRM `*ops-pack*.html` Operator depth / SPECIFIED walls — Owner/ops surfaces, not Haikal Content Engine primary. Do not expand scope.
- API paths `/api/content/ops-depth/*` may remain for Owner/engineering; must not paint into staff Library chrome.

## Shared-fix preference (SPEC binding)
1. Strip AKR / Decision Memory from Content staff grammar (page or shell audience filter).
2. Gate Operator-depth + NAS-index eng panels behind Owner/engineering audience — **not** default LIBRARY view for `SPECIALIST_CONTENT`.
3. Replace staff copy with human lifecycle / empty / progress language per RULE.
4. Keep four primary tabs; demote global nav visually secondary.
5. Do not invent metadata filters; do not mark STAFF READY.

## Hit counts (staff files only)
- `dashboards/assets/sidenav.js`: **3** matching lines
- `dashboards/content-2.0.html`: **20** matching lines
- `scripts/core/wolf_shell.py`: **38** matching lines

## Sample hits (first 40)

| File | Line | Patterns | Snippet |
|------|------|----------|---------|
| `dashboards/content-2.0.html` | 448 | Decision Memory | `<span class="empty">Decision Memory · EMPTY</span>` |
| `dashboards/content-2.0.html` | 449 | \bAKR\b | `<span class="empty">AKR · EMPTY</span>` |
| `dashboards/content-2.0.html` | 542 | Operator depth | `<section class="content-ops-depth" id="content-ops-depth" aria-label="Content operator depth">` |
| `dashboards/content-2.0.html` | 543 | Operator depth | `<h2>Operator depth</h2>` |
| `dashboards/content-2.0.html` | 544 | proven\s*=, ready\s*=, staff_ready\s*=, staff_ready | `<p class="note">Library detail + note / tag / next-action / handoff / dismiss. No Metricool/Klaviyo publish. No Haikal h` |
| `dashboards/content-2.0.html` | 545 | Operator depth | `<div id="contentOpsDepthBody" class="note">Loading operator depth…</div>` |
| `dashboards/content-2.0.html` | 550 | ready\s*=, staff_ready\s*=, staff_ready, human fake | `<p class="note">Browse/filter sampled nas_index (folder · brand · type · recent). Rel paths only. full_tree_indexed=fals` |
| `dashboards/content-2.0.html` | 965 | Operator depth | `/* keep deep-link hash for operator depth */` |
| `dashboards/content-2.0.html` | 1460 | ready\s*=, staff_ready\s*=, staff_ready | `+ '<div class="sub" style="margin:6px 0 0">Brands: ${esc(brands)} · staff_ready=false · human test not signed</div>'` |
| `dashboards/content-2.0.html` | 1485 | operator-depth | `const depth = await api("/api/content/ops-depth/operator-depth");` |
| `dashboards/content-2.0.html` | 1492 | Haikal human | `+ '<div class="note">RBAC content operator ${rbac.can_content_operator ? "yes" : "no"} · CF seat mint no · Haikal human ` |
| `dashboards/content-2.0.html` | 1493 | Needs-You | `+ '<div class="note">Needs-You: ${esc(nxt.label // "EMPTY")} · Owner attention: ${esc(String(attention.count // 0))} · N` |
| `dashboards/content-2.0.html` | 1494 | ready\s*=, staff_ready\s*=, staff_ready | `+ '<div class="note">No Metricool/Klaviyo publish · no invent assets · staff_ready=false</div>';` |
| `dashboards/content-2.0.html` | 1539 | Operator depth | `box.innerHTML = '<p class="err">${esc(err.message // "Operator depth not loaded.")}</p>';` |
| `dashboards/content-2.0.html` | 1556 | NAS destroy, Needs-You | `banner.textContent = "Recorded. GGV Content Needs-You + Owner attention refreshed. No Metricool/Klaviyo publish · no NAS` |
| `dashboards/content-2.0.html` | 1593 | operator-depth | `const depth = await api("/api/nas/index/operator-depth?" + params.toString());` |
| `dashboards/content-2.0.html` | 1601 | ready\s*=, staff_ready\s*=, staff_ready, full_tree_indexed | `+ '<div class="note">full_tree_indexed=false · staff_ready=false · Haikal human not_started · NAS connected: ${nas.nas_c` |
| `dashboards/content-2.0.html` | 1602 | no invent PROVEN | `+ '<div class="note">CAP-GGV-01 ${esc(caps["CAP-GGV-01"] // "?")} · CR ${esc(caps.cr_8c1fa12404180c02 // "OPEN")} stays ` |
| `dashboards/content-2.0.html` | 1647 | full_tree_indexed | `+ '<div class="note">path honesty: rel-only · absolute leak: no · full_tree_indexed=false</div>';` |
| `dashboards/content-2.0.html` | 1669 | ready\s*=, staff_ready\s*=, staff_ready, NAS destroy | `banner.textContent = "Next-action touch recorded. Needs-You / NAS strip refreshed. No Metricool · no NAS destroy · staff` |
| `dashboards/assets/sidenav.js` | 15 | no invent PROVEN | `*   Hidden ≠ permission; API auth is canonical. No invent PROVEN/READY.` |
| `dashboards/assets/sidenav.js` | 53 | Needs You | `{ href: "/staff-ops-routing", title: "Needs You", key: "needs_you" }` |
| `dashboards/assets/sidenav.js` | 119 | Needs You | `{ label: "Needs You", href: null }` |
| `scripts/core/wolf_shell.py` | 46 | operator_depth | `SLICE_NAS_INDEX_OPS = "nas_index_operator_depth"` |
| `scripts/core/wolf_shell.py` | 91 | Needs You | `{"href": NEEDS_YOU_HREF, "title": "Needs You", "key": "needs_you"},` |
| `scripts/core/wolf_shell.py` | 187 | operator-depth | `#   operator-depth: API-only (no *operator-depth*.html / *opdepth* pages)` |
| `scripts/core/wolf_shell.py` | 330 | operator_depth, operator-depth | `"operator_depth_html": [],  # API-only; no *operator-depth* / *opdepth* pages` |
| `scripts/core/wolf_shell.py` | 409 | Decision Memory | `{"key": "decision", "label": "Decision Memory", "href": None, "state": "EMPTY"},` |
| `scripts/core/wolf_shell.py` | 410 | \bAKR\b | `{"key": "akr", "label": "AKR", "href": None, "state": "EMPTY"},` |
| `scripts/core/wolf_shell.py` | 439 | Needs You | `# Content crew: Content under Intelligence→Content + Needs You + assigned GGV brands.` |
| `scripts/core/wolf_shell.py` | 625 | Needs You | `{"label": "Needs You", "href": None},` |
| `scripts/core/wolf_shell.py` | 788 | operator_depth | `"nas_index_operator_depth": True,` |
| `scripts/core/wolf_shell.py` | 792 | operator_depth | `"amg_day_ops_operator_depth": True,` |
| `scripts/core/wolf_shell.py` | 793 | operator_depth | `"amg_packages_operator_depth": True,` |
| `scripts/core/wolf_shell.py` | 794 | operator_depth | `"amg_revenue_yield_operator_depth": True,` |
| `scripts/core/wolf_shell.py` | 795 | operator_depth | `"amg_journey_operator_depth": True,` |
| `scripts/core/wolf_shell.py` | 796 | operator_depth | `"amg_sla_incident_operator_depth": True,` |
| `scripts/core/wolf_shell.py` | 797 | operator_depth | `"amg_service_improve_operator_depth": True,` |
| `scripts/core/wolf_shell.py` | 798 | operator_depth | `"ggv_client_profitability_operator_depth": True,` |
| `scripts/core/wolf_shell.py` | 799 | operator_depth | `"ggv_intercompany_client_operator_depth": True,` |

**Total matching lines:** 61

## Next
Implement via `BF-content-engine-staff-ux-20260924` per SPEC. Peaches verify → Haikal RETEST REQUIRED. staff_ready stays false.

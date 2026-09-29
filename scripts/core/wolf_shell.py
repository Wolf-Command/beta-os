#!/usr/bin/env python3
"""Wolf Global Shell — Wave 1–8 + RHC V1 + Perms + Route Merge/Retire/Redirect (Beta).

Decision / authority:
  docs/RULE-Wolf-Global-Navigation-Design-System-2026-09-22.md
  docs/deliveries/GROK-PLAN-WOLF-ROUTE-MERGE-RETIRE-REDIRECT-2026-09-22.md
  docs/deliveries/GROK-SPEC-WOLF-PERMISSIONS-AUDIENCE-2026-09-22.md
  docs/deliveries/GROK-PLAN-WOLF-PERMISSIONS-AUDIENCE-PROVE-2026-09-22.md (Perms DONE)
  docs/deliveries/GROK-SPEC-WOLF-RESPONSIVE-HIERARCHY-CLEARANCE-2026-09-22.md
  docs/deliveries/GROK-PLAN-WOLF-RESPONSIVE-V1-PROVE-2026-09-22.md (RHC V1 DONE)
  docs/deliveries/GROK-PLAN-WOLF-SHELL-TOKENS-2026-09-22.md (Wave 1 DONE)
  docs/deliveries/GROK-PLAN-WOLF-EMPIRE-HOME-2026-09-22.md (Wave 2 DONE)
  docs/deliveries/GROK-PLAN-WOLF-BZG-UMA-NAV-2026-09-22.md (Wave 3 DONE)
  docs/deliveries/GROK-PLAN-WOLF-GGV-NAV-2026-09-22.md (Wave 4 DONE)
  docs/deliveries/GROK-PLAN-WOLF-AMG-NAV-2026-09-22.md (Wave 5 DONE)
  docs/deliveries/GROK-PLAN-WOLF-INTEL-NAV-2026-09-22.md (Wave 6 DONE)
  docs/deliveries/GROK-PLAN-WOLF-SYSTEM-NAV-2026-09-22.md (Wave 7 DONE)
  docs/deliveries/GROK-PLAN-WOLF-SPECIALIST-NAV-2026-09-22.md (Wave 8 DONE)
  + shell / IA / permissions / page-type / role-nav / target-IA specs 2026-09-22

Bound: beta. Visibility-only whoami filter. Hidden ≠ permission.
API auth remains canonical. No second Boards menu. No PROVEN/READY invent.
Person→Role→Assignment→Scope→Permission→Audience into shell whoami/nav.
Four layers: CAN SEE · CAN ACT · CAN SEE DETAIL · CAN SEE ACROSS SCOPE
(sample Empire + Uma + Progress). Grants by ROLE — no hard-coded people in page logic.
Owner landing = Empire. Devi landing = Uma Blu Today. Amanda landing = GGV Overview.
Coral landing = Atrium/AMG Today/Operations (/amg-ops-pack). Fixture PERS-MISA.
Haikal landing = Content (/content-2.0) under Intelligence→Content. No Owner Intel admin.
Progress under SYSTEM only (Owner). Staff hide SYSTEM admin via nav. Client fail-closed.
RHC: breadcrumbs · UP/BACK/HOME · multi-assignment context switcher · responsive shell.
Wave 8: trading/travel/spartacus/mila/amanda/kuta-rates NOT primary in #wolfnav IA.
Hidden ≠ deleted — soft redirect into Empire (/wolf); no new sprawl pages.
Route merge: redirect > delete. mgmt-cluster → BU parents; legacy uma → /bzg/uma-blu;
dashboards/*.html → clean URLs; radar → Empire priorities; content brand peers → content-2.0.
ACTIVE pack APIs/HTML on disk preserved — top-level bookmarks soft-land only.
"""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any

BOUND = "beta"
SLICE = "wolf_ggv_content_nas_haikal_prep"
SLICE_NAS_INDEX_OPS = "nas_index_operator_depth"
SLICE_PRIOR_NAS_INDEX = "wolf_nas_index_continue"
SLICE_PRIOR_NAS_P0 = "wolf_nas_library_upload_p0"
# Retained for soft-prior source greps (Hidden ≠ wiped).
SLICE_PRIOR_ROUTE = "wolf_route_merge_retire_redirect"
SLICE_PRIOR_PERMS = "wolf_permissions_audience_prove"
SLICE_PRIOR_RHC = "wolf_responsive_v1_prove"
SLICE_PRIOR_WAVE8 = "wolf_specialist_nav_v8"
CACHE_TOKEN = "20260929-mywork1b"
SCHEMA_ID = "wolf.shell-whoami.v1"
EVIDENCE_DIR = Path(__file__).resolve().parents[2] / "docs" / "deliveries" / "evidence" / "wolf-rhc-v1-20260922"
V1_READY_REQUIRES: tuple[str, ...] = (
    "desktop_screenshots",
    "mobile_screenshots",
    "role_matrix_proof",
    "url_api_denial_proof",
    "breadcrumb_back_up_proof",
    "context_switch_proof",
)
CONTENT_HREF = "/content-2.0"
INTEL_HREF = "/intel-ops-pack"

# Clean HOME alias — serves same Empire page; not a second surface.
EMPIRE_HREF = "/owner-empire-pack"
WOLF_ALIAS = "/wolf"
EMPIRE_ALIASES: frozenset[str] = frozenset({EMPIRE_HREF, WOLF_ALIAS})
NEEDS_YOU_HREF = "/staff-ops-routing"
PROGRESS_HREF = "/progress"
INTEGRATIONS_HREF = "/integration-health"
SALE_HREF = "/sale-evidence-pack"

# Primary IA destinations — existing Beta hrefs only. No mgmt-cluster promotion.
# Empire is HOME primary; Progress lives under SYSTEM only (never HOME).
IA_TREE: list[dict[str, Any]] = [
    {
        "id": "home",
        "title": "HOME",
        "items": [
            {
                "href": EMPIRE_HREF,
                "title": "Empire Pulse",
                "key": "empire",
                "primary": True,
                "aliases": [WOLF_ALIAS],
            },
            {"href": NEEDS_YOU_HREF, "title": "Needs You", "key": "needs_you"},
        ],
    },
    {
        "id": "businesses",
        "title": "BUSINESSES",
        "items": [
            {"href": "/ggv-ops-pack", "title": "GGV", "key": "ggv"},
            {"href": "/amg-ops-pack", "title": "Atrium / AMG", "key": "amg"},
            {"href": "/bzg", "title": "Blu Zone / BZG", "key": "bzg"},
            {"href": "/bzg/uma-blu", "title": "Uma Blu · Today", "key": "uma"},
        ],
    },
    {
        "id": "intelligence",
        "title": "INTELLIGENCE",
        "items": [
            {"href": INTEL_HREF, "title": "Intelligence Home", "key": "intel"},
            {"href": CONTENT_HREF, "title": "Content", "key": "content"},
        ],
    },
    {
        "id": "system",
        "title": "SYSTEM",
        "items": [
            {"href": PROGRESS_HREF, "title": "Progress", "key": "progress"},
            {"href": INTEGRATIONS_HREF, "title": "Integrations", "key": "integrations"},
            {"href": SALE_HREF, "title": "Sale Readiness", "key": "sale"},
        ],
    },
]

ALL_HREFS: list[str] = [
    it["href"] for sec in IA_TREE for it in sec["items"]
]

# Wave 8 — legacy specialist boards retired from primary IA (Target IA + merge plan #8).
# Hidden ≠ deleted: soft-redirect into Empire HOME (/wolf). No new sprawl pages.
# Trading execution stays refused elsewhere (Flint reserved) — these are chrome paths only.
SPECIALIST_PRIMARY_SLUGS: frozenset[str] = frozenset(
    {
        "trading",
        "travel",
        "spartacus",
        "mila",
        "amanda",
        "kuta-rates",
    }
)
SPECIALIST_PRIMARY_KEYS: frozenset[str] = frozenset(
    {
        "trading",
        "travel",
        "spartacus",
        "mila",
        "amanda",
        "kuta_rates",
        "kuta-rates",
        "specialist",
    }
)
SPECIALIST_SOFT_REDIRECT_TARGET = WOLF_ALIAS
# Paths that used to sit as Boards peers — redirect only; capability preserved via Empire.
SPECIALIST_SOFT_REDIRECT_PATHS: frozenset[str] = frozenset(
    {
        "/trading",
        "/trading/",
        "/trading.html",
        "/dashboards/trading.html",
        "/travel",
        "/travel/",
        "/travel.html",
        "/dashboards/travel.html",
        "/spartacus",
        "/spartacus/",
        "/spartacus.html",
        "/dashboards/spartacus.html",
        "/mila",
        "/mila/",
        "/mila.html",
        "/dashboards/mila.html",
        "/amanda",
        "/amanda/",
        "/amanda.html",
        "/dashboards/amanda.html",
        "/kuta-rates",
        "/kuta-rates/",
        "/kuta-rates.html",
        "/dashboards/kuta-rates.html",
    }
)

# ---------------------------------------------------------------------------
# Route merge / retire / redirect (plan 2026-09-22) — redirect > delete.
# Inventory (Mac Beta tree, 2026-09-22):
#   mgmt-cluster HTML: 11 under dashboards/*-mgmt-cluster.html (no /mgmt-cluster/ dir)
#   operator-depth: API-only (no *operator-depth*.html / *opdepth* pages)
#   legacy uma: /uma-blu(+.html) + /dashboards/uma-blu.html (no uma-blu.html file)
#   content brand peers: none on disk (only content-2.0.html) — alias redirects only
#   radar: radar-prove.html ACTIVE pack kept; standalone /radar(.html) → Empire priorities
#   duplicate dashboards/*.html: many aliases → clean URL 302
# ACTIVE factory pack APIs + HTML files preserved on disk; top-level soft-land only.
# ---------------------------------------------------------------------------
EMPIRE_PRIORITIES_HREF = "/wolf#priorities"

# mgmt-cluster top-level → owning BU / SYSTEM / Empire (drop primary sprawl).
MGMT_CLUSTER_REDIRECTS: dict[str, str] = {
    "bzg-mgmt-cluster": "/bzg",
    "ggv-mgmt-cluster": "/ggv-ops-pack",
    "amg-mgmt-cluster": "/amg-ops-pack",
    "intel-mgmt-cluster": "/intel-ops-pack",
    "core-mgmt-cluster": "/progress",
    "crm-mgmt-cluster": "/lead-spine",
    "msc-mgmt-cluster": "/progress",
    "strat-mgmt-cluster": EMPIRE_PRIORITIES_HREF,
    "dr-mgmt-cluster": "/progress",
    "sale-mgmt-cluster": "/sale-evidence-pack",
    "intg-mgmt-cluster": "/integration-health",
}

# Legacy Uma → canonical Uma Today.
LEGACY_UMA_REDIRECTS: dict[str, str] = {
    "/uma-blu": "/bzg/uma-blu",
    "/uma-blu/": "/bzg/uma-blu",
    "/uma-blu.html": "/bzg/uma-blu",
    "/dashboards/uma-blu.html": "/bzg/uma-blu",
}

# Standalone radar → Empire HOME priorities (radar-prove pack route stays live).
RADAR_REDIRECTS: dict[str, str] = {
    "/radar": EMPIRE_PRIORITIES_HREF,
    "/radar/": EMPIRE_PRIORITIES_HREF,
    "/radar.html": EMPIRE_PRIORITIES_HREF,
    "/dashboards/radar.html": EMPIRE_PRIORITIES_HREF,
}

# Per-brand content peers → Content workspace + brand context (no peer HTML on disk).
CONTENT_BRAND_REDIRECTS: dict[str, str] = {
    "/content-habitat": "/content-2.0?brand=habitat",
    "/content-habitat.html": "/content-2.0?brand=habitat",
    "/dashboards/content-habitat.html": "/content-2.0?brand=habitat",
    "/content-ggv": "/content-2.0?brand=ggv",
    "/content-ggv.html": "/content-2.0?brand=ggv",
    "/dashboards/content-ggv.html": "/content-2.0?brand=ggv",
    "/content-amg": "/content-2.0?brand=amg",
    "/content-amg.html": "/content-2.0?brand=amg",
    "/dashboards/content-amg.html": "/content-2.0?brand=amg",
    "/content-bzg": "/content-2.0?brand=bzg",
    "/content-bzg.html": "/content-2.0?brand=bzg",
    "/dashboards/content-bzg.html": "/content-2.0?brand=bzg",
    "/content-uma": "/content-2.0?brand=uma",
    "/content-uma.html": "/content-2.0?brand=uma",
    "/dashboards/content-uma.html": "/content-2.0?brand=uma",
}

# Duplicate /dashboards/<slug>.html → clean canonical (302). Keep serving clean path.
# Top pack surfaces + Uma deep links + plan-named aliases.
DASHBOARDS_HTML_CANONICAL: dict[str, str] = {
    "/dashboards/progress.html": "/progress",
    "/dashboards/integration-health.html": "/integration-health",
    "/dashboards/sale-evidence-pack.html": "/sale-evidence-pack",
    "/dashboards/owner-empire-pack.html": "/owner-empire-pack",
    "/dashboards/staff-ops-routing.html": "/staff-ops-routing",
    "/dashboards/my-work.html": "/my-work",
    "/dashboards/ggv-ops-pack.html": "/ggv-ops-pack",
    "/dashboards/ggv-finance.html": "/ggv/finance",
    "/dashboards/amg-ops-pack.html": "/amg-ops-pack",
    "/dashboards/amg-daily-ops-state.html": "/amg-daily-ops-state",
    "/dashboards/amg-os-shell.html": "/amg/os-shell",
    "/amg-os-shell.html": "/amg/os-shell",
    "/amg-os-shell": "/amg/os-shell",
    "/amg-os-shell/": "/amg/os-shell",
    "/dashboards/ggv-content-prove.html": "/ggv/content-prove",
    "/ggv-content-prove.html": "/ggv/content-prove",
    "/ggv-content-prove": "/ggv/content-prove",
    "/ggv-content-prove/": "/ggv/content-prove",
    "/dashboards/ggv-pipeline-truth-1.html": "/ggv/pipeline-truth-1",
    "/ggv-pipeline-truth-1.html": "/ggv/pipeline-truth-1",
    "/ggv-pipeline-truth-1": "/ggv/pipeline-truth-1",
    "/ggv-pipeline-truth-1/": "/ggv/pipeline-truth-1",
    "/ggv-pipeline": "/ggv/pipeline-truth-1",
    "/ggv-pipeline/": "/ggv/pipeline-truth-1",
    "/dashboards/crm-identity-1.html": "/crm/identity-1",
    "/crm-identity-1.html": "/crm/identity-1",
    "/crm-identity-1": "/crm/identity-1",
    "/crm-identity-1/": "/crm/identity-1",
    "/dashboards/fin-interco-1.html": "/fin/interco-1",
    "/fin-interco-1.html": "/fin/interco-1",
    "/fin-interco-1": "/fin/interco-1",
    "/fin-interco-1/": "/fin/interco-1",
    "/dashboards/fin-recon-shell-1.html": "/fin/recon-shell-1",
    "/fin-recon-shell-1.html": "/fin/recon-shell-1",
    "/fin-recon-shell-1": "/fin/recon-shell-1",
    "/fin-recon-shell-1/": "/fin/recon-shell-1",
    "/dashboards/fin-ap-ar-shell-1.html": "/fin/ap-ar-shell-1",
    "/fin-ap-ar-shell-1.html": "/fin/ap-ar-shell-1",
    "/fin-ap-ar-shell-1": "/fin/ap-ar-shell-1",
    "/fin-ap-ar-shell-1/": "/fin/ap-ar-shell-1",
    "/dashboards/owner-needs-you-1.html": "/owner/needs-you-1",
    "/owner-needs-you-1.html": "/owner/needs-you-1",
    "/owner-needs-you-1": "/owner/needs-you-1",
    "/owner-needs-you-1/": "/owner/needs-you-1",
    "/dashboards/esb-truth-1.html": "/ops/esb-truth-1",
    "/esb-truth-1.html": "/ops/esb-truth-1",
    "/esb-truth-1": "/ops/esb-truth-1",
    "/esb-truth-1/": "/ops/esb-truth-1",
    "/dashboards/conn-health-1.html": "/ops/conn-health-1",
    "/conn-health-1.html": "/ops/conn-health-1",
    "/conn-health-1": "/ops/conn-health-1",
    "/conn-health-1/": "/ops/conn-health-1",
    "/conn-health": "/ops/conn-health-1",
    "/conn-health/": "/ops/conn-health-1",
    "/dashboards/backup-health-1.html": "/ops/backup-health-1",
    "/backup-health-1.html": "/ops/backup-health-1",
    "/backup-health-1": "/ops/backup-health-1",
    "/backup-health-1/": "/ops/backup-health-1",
    "/backup-health": "/ops/backup-health-1",
    "/backup-health/": "/ops/backup-health-1",
    "/dashboards/fin-cash-truth-1.html": "/fin/cash-truth-1",
    "/fin-cash-truth-1.html": "/fin/cash-truth-1",
    "/fin-cash-truth-1": "/fin/cash-truth-1",
    "/fin-cash-truth-1/": "/fin/cash-truth-1",
    "/fin-cash-truth": "/fin/cash-truth-1",
    "/fin-cash-truth/": "/fin/cash-truth-1",
    "/dashboards/bzg-labor-cost-1.html": "/bzg/labor-cost-1",
    "/bzg-labor-cost-1.html": "/bzg/labor-cost-1",
    "/bzg-labor-cost-1": "/bzg/labor-cost-1",
    "/bzg-labor-cost-1/": "/bzg/labor-cost-1",
    "/bzg-labor-cost": "/bzg/labor-cost-1",
    "/bzg-labor-cost/": "/bzg/labor-cost-1",
    "/dashboards/intel-ops-pack.html": "/intel-ops-pack",
    "/dashboards/content-2.0.html": "/content-2.0",
    "/dashboards/habitat-operator.html": "/habitat-operator",
    "/dashboards/lead-spine.html": "/lead-spine",
    "/dashboards/bzg.html": "/bzg",
    "/dashboards/bzg-uma-blu.html": "/bzg/uma-blu",
    "/dashboards/bzg-uma-blu-bills.html": "/bzg/uma-blu/bills",
    "/dashboards/bzg-uma-blu-issues.html": "/bzg/uma-blu/issues",
    "/dashboards/bzg-uma-blu-petty.html": "/bzg/uma-blu/petty",
    "/dashboards/bzg-uma-blu-evidence.html": "/bzg/uma-blu/evidence",
    "/dashboards/bzg-uma-blu-exceptions.html": "/bzg/uma-blu/exceptions",
    "/dashboards/bzg-uma-blu-pr.html": "/bzg/uma-blu/bills",
    "/dashboards/uma-blu-close.html": "/uma-blu-close",
    "/dashboards/v1-status.html": "/ops/v1-status",
    "/dashboards/integrations-status.html": "/ops/integrations-status",
    "/integrations-status.html": "/ops/integrations-status",
    "/dashboards/reliability.html": "/ops/reliability",
    "/reliability.html": "/ops/reliability",
    "/dashboards/content-engine-live.html": "/ops/content-engine-live",
    "/content-engine-live.html": "/ops/content-engine-live",
    "/content-engine-live": "/ops/content-engine-live",
    "/content-engine-live/": "/ops/content-engine-live",
    "/content/engine-live": "/ops/content-engine-live",
    "/content/engine-live/": "/ops/content-engine-live",
    # Flat legacy filenames that used to sit next to clean routes
    "/bzg-uma-blu.html": "/bzg/uma-blu",
    "/bzg-uma-blu": "/bzg/uma-blu",
    "/bzg-uma-blu/": "/bzg/uma-blu",
}

# V1-SWEEP-1 — superseded / historical V1 finance board aliases → Beta canonical.
# HR surfaces intentionally omitted. Does not delete wolf-system V1 files.
V1_SUPERSEDED_BOARD_REDIRECTS: dict[str, str] = {
    "/atrium-finance": "/amg/finance",
    "/atrium-finance/": "/amg/finance",
    "/atrium-finance.html": "/amg/finance",
    "/dashboards/atrium-finance.html": "/amg/finance",
    "/bzg-finance": "/bzg/finance",
    "/bzg-finance.html": "/bzg/finance",
    "/dashboards/bzg-finance.html": "/bzg/finance",
}


def _mgmt_cluster_path_variants(slug: str, dest: str) -> dict[str, str]:
    """Expand slug → path variants mapping to dest."""
    base = slug if slug.startswith("/") else f"/{slug}"
    return {
        base: dest,
        f"{base}/": dest,
        f"{base}.html": dest,
        f"/dashboards/{slug}.html": dest,
    }


def _build_route_merge_redirects() -> dict[str, str]:
    out: dict[str, str] = {}
    out.update(LEGACY_UMA_REDIRECTS)
    out.update(RADAR_REDIRECTS)
    out.update(CONTENT_BRAND_REDIRECTS)
    out.update(DASHBOARDS_HTML_CANONICAL)
    out.update(V1_SUPERSEDED_BOARD_REDIRECTS)
    for slug, dest in MGMT_CLUSTER_REDIRECTS.items():
        out.update(_mgmt_cluster_path_variants(slug, dest))
    return out


ROUTE_MERGE_REDIRECTS: dict[str, str] = _build_route_merge_redirects()


def route_merge_redirect_target(path: str | None) -> str | None:
    """Return 302 Location for retired/duplicate top-level paths, else None.

    Does not touch /api/* (capability preserved). Specialist soft-redirect is
    separate (Wave 8). ACTIVE pack HTML/APIs stay on disk — bookmarks soft-land.
    """
    raw = (path or "").split("?")[0].split("#")[0]
    if not raw:
        return None
    if not raw.startswith("/"):
        raw = "/" + raw
    if raw.startswith("/api/"):
        return None
    # Exact table hit
    if raw in ROUTE_MERGE_REDIRECTS:
        return ROUTE_MERGE_REDIRECTS[raw]
    # Trailing-slash normalized
    stripped = raw.rstrip("/") or "/"
    if stripped in ROUTE_MERGE_REDIRECTS:
        return ROUTE_MERGE_REDIRECTS[stripped]
    # /dashboards/<file>.html generic → /<stem> when stem is a known clean surface
    # already enumerated; no invent of arbitrary redirects.
    return None


def route_merge_inventory() -> dict[str, Any]:
    """Mac Beta inventory snapshot for prove / review (find-before-mass-retire)."""
    return {
        "mgmt_cluster_html": sorted(MGMT_CLUSTER_REDIRECTS.keys()),
        "mgmt_cluster_dir": None,  # no /mgmt-cluster/ tree found
        "operator_depth_html": [],  # API-only; no *operator-depth* / *opdepth* pages
        "legacy_uma_paths": sorted(LEGACY_UMA_REDIRECTS.keys()),
        "content_brand_peer_html_on_disk": [],  # only content-2.0.html present
        "content_brand_aliases": sorted(CONTENT_BRAND_REDIRECTS.keys()),
        "radar_standalone": sorted(RADAR_REDIRECTS.keys()),
        "radar_prove_kept": True,  # ACTIVE strat pack — not mass-retired
        "dashboards_html_canonical_count": len(DASHBOARDS_HTML_CANONICAL),
        "redirect_table_size": len(ROUTE_MERGE_REDIRECTS),
        "specialist_soft_redirect_retained": True,
        "progress_factory_integ_sale_under_system": True,
        "one_wolfnav_owner": True,
    }

# Soft-land role landings via whoami (visibility only — not auth grants).
# Owner → Empire (/wolf). Devi/ops → Uma Blu Today (/bzg/uma-blu).
MY_WORK_HREF = "/my-work"
LANDING_BY_AUDIENCE: dict[str, str | None] = {
    "OWNER": WOLF_ALIAS,
    "SYSTEM": WOLF_ALIAS,
    "EXECUTIVE": EMPIRE_HREF,
    "OPERATOR": "/bzg/uma-blu",
    "SPECIALIST_GGV": "/ggv-ops-pack",
    "SPECIALIST_AMG": "/amg-ops-pack",
    "SPECIALIST_CONTENT": CONTENT_HREF,
    "SPECIALIST_FINANCE": MY_WORK_HREF,
    "SPECIALIST_ATRIUM_FINANCE": "/amg/finance",
    "CLIENT": None,
}

# Business grammar labels — stable. Missing pages = EMPTY (never fake %).
BZG_GRAMMAR: list[dict[str, Any]] = [
    {"key": "overview", "label": "Overview", "href": "/bzg", "state": "live"},
    {"key": "operations", "label": "Operations", "href": "/bzg/ops-desk", "state": "live"},
    {"key": "outlets", "label": "Outlets", "href": "/bzg/outlets", "state": "live"},
    {"key": "venue_pnl", "label": "Venue P&L", "href": "/bzg/venue-pnl", "state": "live"},
    {"key": "waste_yield", "label": "Waste / Yield", "href": "/bzg/waste-yield", "state": "live"},
    {"key": "labor_cost", "label": "Labor Cost", "href": "/bzg/labor-cost-1", "state": "live"},
    {"key": "issues", "label": "Issues", "href": None, "state": "EMPTY"},
    {"key": "finance", "label": "Finance", "href": "/bzg/finance", "state": "live"},
    {"key": "people", "label": "People", "href": None, "state": "EMPTY"},
    {"key": "customers", "label": "Customers", "href": None, "state": "EMPTY"},
    {"key": "standards", "label": "Standards", "href": None, "state": "EMPTY"},
    {"key": "intelligence", "label": "Intelligence", "href": None, "state": "EMPTY"},
]

UMA_GRAMMAR: list[dict[str, Any]] = [
    {"key": "today", "label": "Today", "href": "/bzg/uma-blu", "state": "live"},
    {"key": "overview", "label": "Overview", "href": None, "state": "EMPTY"},
    {"key": "operations", "label": "Operations", "href": None, "state": "EMPTY"},
    {"key": "bills", "label": "Bills", "href": "/bzg/uma-blu/bills", "state": "live"},
    {"key": "issues", "label": "Issues", "href": "/bzg/uma-blu/issues", "state": "live"},
    {"key": "petty", "label": "Petty", "href": "/bzg/uma-blu/petty", "state": "live"},
    {"key": "recipes", "label": "Recipes", "href": "/bzg/uma-blu/recipes", "state": "live"},
    {"key": "close", "label": "Close", "href": "/uma-blu-close", "state": "live"},
]

# GGV business grammar — Overview live on existing /ggv-ops-pack.
# Finance is the bounded nota desk (not Zayen books). Other slots stay EMPTY.
GGV_GRAMMAR: list[dict[str, Any]] = [
    {"key": "overview", "label": "Overview", "href": "/ggv-ops-pack", "state": "live"},
    {"key": "operations", "label": "Operations", "href": None, "state": "EMPTY"},
    {"key": "pipeline", "label": "Pipeline", "href": "/ggv/pipeline-truth-1", "state": "live"},
    {"key": "people", "label": "People", "href": None, "state": "EMPTY"},
    {"key": "customers", "label": "Customers", "href": None, "state": "EMPTY"},
    {"key": "finance", "label": "Finance", "href": "/ggv/finance", "state": "live"},
    {"key": "standards", "label": "Standards", "href": None, "state": "EMPTY"},
    {"key": "issues", "label": "Issues", "href": None, "state": "EMPTY"},
    {"key": "intelligence", "label": "Intelligence", "href": None, "state": "EMPTY"},
]

# AMG / Atrium grammar — Overview+Operations soft-land on existing /amg-ops-pack (Today desk).
# Finance nested/visible-only EMPTY — never money/Zayen execution. No fake %.
AMG_GRAMMAR: list[dict[str, Any]] = [
    {"key": "overview", "label": "Overview", "href": "/amg-ops-pack", "state": "live"},
    {"key": "operations", "label": "Operations", "href": "/amg-ops-pack", "state": "live"},
    {"key": "people", "label": "People", "href": None, "state": "EMPTY"},
    {"key": "customers", "label": "Customers", "href": None, "state": "EMPTY"},
    {"key": "finance", "label": "Finance", "href": None, "state": "EMPTY"},
    {"key": "standards", "label": "Standards", "href": None, "state": "EMPTY"},
    {"key": "issues", "label": "Issues", "href": None, "state": "EMPTY"},
    {"key": "intelligence", "label": "Intelligence", "href": None, "state": "EMPTY"},
]

# Intelligence grammar — Home soft-land /intel-ops-pack; Content live /content-2.0.
# Rest EMPTY (never fake %). Inherits requester perms — not a side door.
INTEL_GRAMMAR: list[dict[str, Any]] = [
    {"key": "home", "label": "Home", "href": INTEL_HREF, "state": "live"},
    {"key": "content", "label": "Content", "href": CONTENT_HREF, "state": "live"},
    {"key": "brand", "label": "Brand / Competitive", "href": None, "state": "EMPTY"},
    {"key": "decision", "label": "Decision Memory", "href": None, "state": "EMPTY"},
    {"key": "akr", "label": "AKR", "href": None, "state": "EMPTY"},
]

# SYSTEM grammar — Progress soft-land home; Integrations + Sale live existing surfaces.
# Factory EMPTY (no sprawl page). Never fake %. Owner-only via audience pages.
SYSTEM_GRAMMAR: list[dict[str, Any]] = [
    {"key": "progress", "label": "Progress", "href": PROGRESS_HREF, "state": "live"},
    {"key": "integrations", "label": "Integrations", "href": INTEGRATIONS_HREF, "state": "live"},
    {"key": "sale", "label": "Sale Readiness", "href": SALE_HREF, "state": "live"},
    {"key": "factory", "label": "Factory / Health", "href": None, "state": "EMPTY"},
]

# Fixture projections (Person→Role→Assignment→Scope→Audience). Tests/docs only.
# Do not hard-code people in page business logic — shell visibility map only.
AUDIENCE_PAGES: dict[str, list[str]] = {
    "OWNER": list(ALL_HREFS),
    "EXECUTIVE": [
        EMPIRE_HREF,
        NEEDS_YOU_HREF,
        "/ggv-ops-pack",
        "/amg-ops-pack",
        "/bzg",
        "/bzg/uma-blu",
        INTEL_HREF,
        CONTENT_HREF,
    ],
    "OPERATOR": [NEEDS_YOU_HREF, "/bzg/uma-blu", "/bzg", "/bzg/recipe-builder"],
    "SPECIALIST_GGV": [NEEDS_YOU_HREF, "/ggv-ops-pack", "/ggv/finance"],
    "SPECIALIST_AMG": [NEEDS_YOU_HREF, "/amg-ops-pack"],
    # Content crew: Content under Intelligence→Content + Needs You + assigned GGV brands.
    # Never Owner Intelligence Home (/intel-ops-pack) via nav alone.
    "SPECIALIST_CONTENT": [NEEDS_YOU_HREF, CONTENT_HREF, "/ggv-ops-pack"],
    "SPECIALIST_FINANCE": [MY_WORK_HREF, "/ggv/finance"],
    # CORE-ENT-1: AMG primary + BZG finance entry; GGV stays off this audience.
    "SPECIALIST_ATRIUM_FINANCE": [MY_WORK_HREF, "/amg/finance", "/bzg/finance"],
    "CLIENT": [],  # controlled projection — never inherit operator Boards
    "SYSTEM": list(ALL_HREFS),
}

# Job → chrome audience for a person who is not in the fixture map.
# Known people keep PERSON_AUDIENCE so existing seats do not move.
ROLE_AUDIENCE: dict[str, str] = {
    "ROLE-OWNER": "OWNER",
    "ROLE-GGV-CREATIVE-DIRECTOR": "SPECIALIST_CONTENT",
    "ROLE-CONTENT": "SPECIALIST_CONTENT",
    "ROLE-CONTENT-MGMT": "SPECIALIST_CONTENT",
    "ROLE-CONTENT-CREW": "SPECIALIST_CONTENT",
    "ROLE-CONTENT-CREATOR": "SPECIALIST_CONTENT",
    "ROLE-BZG-FB-OPS-LEAD": "OPERATOR",
    "ROLE-BZG-HFB": "OPERATOR",
    "ROLE-BZG-CLOSER": "OPERATOR",
    "ROLE-BZG-HEAD-CHEF": "OPERATOR",
    "ROLE-GGV-LEAD": "SPECIALIST_GGV",
    "ROLE-AMG-OPS": "SPECIALIST_AMG",
    "ROLE-AMG-GM": "SPECIALIST_AMG",
    "ROLE-GGV-EXTERNAL-ACCOUNTANT": "SPECIALIST_FINANCE",
    "ROLE-GGV-FINANCE-OPERATOR": "SPECIALIST_FINANCE",
    "ROLE-AMG-FINANCE-OFFICER": "SPECIALIST_ATRIUM_FINANCE",
    "ROLE-AMG-FINANCIAL-CONTROLLER": "SPECIALIST_ATRIUM_FINANCE",
    "ROLE-AMG-ACCOUNTS-PAYABLE": "SPECIALIST_ATRIUM_FINANCE",
    "ROLE-AMG-ACCOUNTS-RECEIVABLE": "SPECIALIST_ATRIUM_FINANCE",
    "ROLE-AMG-EXTERNAL-ACCOUNTANT": "SPECIALIST_ATRIUM_FINANCE",
    "ROLE-BZG-FINANCIAL-CONTROLLER": "SPECIALIST_ATRIUM_FINANCE",
    "ROLE-BZG-EXTERNAL-ACCOUNTANT": "SPECIALIST_ATRIUM_FINANCE",
}

PERSON_AUDIENCE: dict[str, str] = {
    "PERS-MATT": "OWNER",
    "PERS-DEVI": "OPERATOR",
    "PERS-AMANDA": "SPECIALIST_GGV",
    "PERS-HAIKAL": "SPECIALIST_CONTENT",
    "PERS-MISA": "SPECIALIST_AMG",
}

PERSON_HELLO: dict[str, str] = {
    "PERS-MATT": "Owner",
    "PERS-DEVI": "BZG ops",
    "PERS-AMANDA": "GGV",
    "PERS-HAIKAL": "Content",
    "PERS-MISA": "Coral",  # Coral / AMG ops fixture (role-nav matrix)
}

# Fixture assignments (Person→Role→Assignment→Scope). Chrome visibility only.
# Context switcher shows only when len(assignments) > 1. Never invent unauthorised scopes.
PERSON_ASSIGNMENTS: dict[str, list[dict[str, Any]]] = {
    "PERS-MATT": [
        {
            "id": "ASG-OWNER-EMPIRE",
            "role": "ROLE-OWNER",
            "label": "Empire",
            "scope": "SCOPE-WOLF-GROUP",
            "href": WOLF_ALIAS,
        },
        {
            "id": "ASG-OWNER-BZG",
            "role": "ROLE-OWNER",
            "label": "BZG",
            "scope": "SCOPE-BZG-ENTITY",
            "href": "/bzg",
        },
        {
            "id": "ASG-OWNER-GGV",
            "role": "ROLE-OWNER",
            "label": "GGV",
            "scope": "SCOPE-GGV",
            "href": "/ggv-ops-pack",
        },
        {
            "id": "ASG-OWNER-AMG",
            "role": "ROLE-OWNER",
            "label": "AMG",
            "scope": "SCOPE-AMG",
            "href": "/amg-ops-pack",
        },
    ],
    "PERS-DEVI": [
        {
            "id": "ASG-BZG-UMA-OPS",
            "role": "ROLE-BZG-FB-OPS-LEAD",
            "label": "Uma Blu",
            "scope": "SCOPE-BZG-UMA",
            "href": "/bzg/uma-blu",
        },
    ],
    "PERS-AMANDA": [
        {
            "id": "ASG-GGV-LEAD",
            "role": "ROLE-GGV-LEAD",
            "label": "GGV",
            "scope": "SCOPE-GGV",
            "href": "/ggv-ops-pack",
        },
    ],
    "PERS-HAIKAL": [
        {
            "id": "ASG-GGV-CONTENT",
            "role": "ROLE-CONTENT",
            "label": "Content",
            "scope": "SCOPE-GGV-CONTENT",
            "href": CONTENT_HREF,
        },
    ],
    "PERS-MISA": [
        {
            "id": "ASG-AMG-OPS",
            "role": "ROLE-AMG-OPS",
            "label": "Atrium / AMG",
            "scope": "SCOPE-AMG",
            "href": "/amg-ops-pack",
        },
    ],
}

# Four control layers (Permissions Audience spec §2). Separate grants.
PERM_LAYERS: tuple[str, ...] = (
    "CAN_SEE",
    "CAN_ACT",
    "CAN_SEE_DETAIL",
    "CAN_SEE_ACROSS_SCOPE",
)

# Sample prove surfaces — Empire + Uma + Progress (plan §3).
SAMPLE_SURFACES: dict[str, dict[str, Any]] = {
    "empire": {
        "href": EMPIRE_HREF,
        "aliases": list(EMPIRE_ALIASES),
        "scope": "SCOPE-WOLF-GROUP",
        "label": "Empire Pulse",
    },
    "uma": {
        "href": "/bzg/uma-blu",
        "aliases": [],
        "scope": "SCOPE-BZG-UMA",
        "label": "Uma Blu Today",
    },
    "progress": {
        "href": PROGRESS_HREF,
        "aliases": [],
        "scope": "SCOPE-SYSTEM",
        "label": "Progress",
    },
}

# Role → surface → layer grants. ROLE codes only — never person names in page logic.
# OWNER: full four layers on samples. OPERATOR (BZG F&B): Uma CAN_SEE+CAN_ACT only
# (no DETAIL / no ACROSS). Content/GGV/AMG roles: no Empire/Uma/Progress sample grants.
_EMPTY_SAMPLE: dict[str, frozenset[str]] = {
    "empire": frozenset(),
    "uma": frozenset(),
    "progress": frozenset(),
}
ROLE_SURFACE_LAYERS: dict[str, dict[str, frozenset[str]]] = {
    "ROLE-OWNER": {
        "empire": frozenset(PERM_LAYERS),
        "uma": frozenset(PERM_LAYERS),
        "progress": frozenset(PERM_LAYERS),
    },
    "ROLE-BZG-FB-OPS-LEAD": {
        "empire": frozenset(),
        "uma": frozenset({"CAN_SEE", "CAN_ACT"}),
        "progress": frozenset(),
    },
    "ROLE-GGV-LEAD": dict(_EMPTY_SAMPLE),
    "ROLE-CONTENT": dict(_EMPTY_SAMPLE),
    "ROLE-AMG-OPS": dict(_EMPTY_SAMPLE),
}

# Hierarchy map: path → parent href (None = root / no UP).
ROUTE_PARENT: dict[str, str | None] = {
    EMPIRE_HREF: None,
    WOLF_ALIAS: None,
    NEEDS_YOU_HREF: EMPIRE_HREF,
    "/ggv-ops-pack": EMPIRE_HREF,
    "/ggv/finance": "/ggv-ops-pack",
    "/ggv/content-prove": "/ggv-ops-pack",
    "/ggv/pipeline-truth-1": "/ggv-ops-pack",
    "/ggv/pipeline": "/ggv-ops-pack",
    "/ops/content-engine-live": EMPIRE_HREF,
    "/crm/identity-1": EMPIRE_HREF,
    "/fin/interco-1": EMPIRE_HREF,
    "/fin/recon-shell-1": EMPIRE_HREF,
    "/fin/cash-truth-1": EMPIRE_HREF,
    "/fin/ap-ar-shell-1": EMPIRE_HREF,
    "/owner/needs-you-1": EMPIRE_HREF,
    "/ops/esb-truth-1": PROGRESS_HREF,
    "/ops/conn-health-1": PROGRESS_HREF,
    "/ops/conn-health": PROGRESS_HREF,
    "/crm-identity": EMPIRE_HREF,
    "/habitat-operator": "/ggv-ops-pack",
    "/lead-spine": "/ggv-ops-pack",
    "/amg-ops-pack": EMPIRE_HREF,
    "/amg-daily-ops-state": "/amg-ops-pack",
    "/amg/os-shell": "/amg-ops-pack",
    "/amg/finance": None,
    "/amg/finance/ledger": "/amg/finance",
    "/amg/finance/accounts": "/amg/finance",
    "/amg/finance/journals": "/amg/finance",
    "/amg/finance/reports": "/amg/finance",
    "/amg/finance/approvals": "/amg/finance",
    "/bzg": EMPIRE_HREF,
    "/bzg/finance": "/bzg",
    "/bzg/outlets": "/bzg",
    "/bzg/ops-desk": "/bzg",
    "/bzg/ops": "/bzg",
    "/bzg/venue-pnl": "/bzg",
    "/bzg/waste-yield": "/bzg",
    "/bzg/waste-yield-desk": "/bzg",
    "/bzg/labor-cost-1": "/bzg",
    "/bzg/labor-cost": "/bzg",
    "/bzg/uma-blu": "/bzg",
    "/bzg/uma-blu/bills": "/bzg/uma-blu",
    "/bzg/uma-blu/issues": "/bzg/uma-blu",
    "/bzg/uma-blu/petty": "/bzg/uma-blu",
    "/uma-blu-close": "/bzg/uma-blu",
    "/bzg/uma-blu/evidence": "/bzg/uma-blu",
    "/bzg/uma-blu/exceptions": "/bzg/uma-blu",
    INTEL_HREF: EMPIRE_HREF,
    CONTENT_HREF: INTEL_HREF,
    # Wave 7: Progress = System soft-land home; children UP → Progress.
    PROGRESS_HREF: EMPIRE_HREF,
    INTEGRATIONS_HREF: PROGRESS_HREF,
    SALE_HREF: PROGRESS_HREF,
}

# Breadcrumb trails (last crumb = current; href None = current page).
# BZG/Uma: WOLF › Blu Zone › Uma Blu › Today
# GGV/Habitat: WOLF › Goss Group › GGV › …
ROUTE_CRUMBS: dict[str, list[dict[str, Any]]] = {
    EMPIRE_HREF: [
        {"label": "HOME", "href": WOLF_ALIAS},
        {"label": "Empire Pulse", "href": None},
    ],
    WOLF_ALIAS: [
        {"label": "HOME", "href": WOLF_ALIAS},
        {"label": "Empire Pulse", "href": None},
    ],
    NEEDS_YOU_HREF: [
        {"label": "HOME", "href": WOLF_ALIAS},
        {"label": "Needs You", "href": None},
    ],
    "/ggv-ops-pack": [
        {"label": "WOLF", "href": WOLF_ALIAS},
        {"label": "Goss Group", "href": None},
        {"label": "GGV", "href": None},
    ],
    "/habitat-operator": [
        {"label": "WOLF", "href": WOLF_ALIAS},
        {"label": "Goss Group", "href": None},
        {"label": "GGV", "href": "/ggv-ops-pack"},
        {"label": "Habitat", "href": None},
    ],
    "/lead-spine": [
        {"label": "WOLF", "href": WOLF_ALIAS},
        {"label": "Goss Group", "href": None},
        {"label": "GGV", "href": "/ggv-ops-pack"},
        {"label": "Lead Spine", "href": None},
    ],
    "/ggv/finance": [
        {"label": "WOLF", "href": WOLF_ALIAS},
        {"label": "Goss Group", "href": None},
        {"label": "GGV", "href": "/ggv-ops-pack"},
        {"label": "Finance", "href": None},
    ],
    "/ggv/content-prove": [
        {"label": "WOLF", "href": WOLF_ALIAS},
        {"label": "Goss Group", "href": None},
        {"label": "GGV", "href": "/ggv-ops-pack"},
        {"label": "Content Prove", "href": None},
    ],
    "/ggv/pipeline-truth-1": [
        {"label": "WOLF", "href": WOLF_ALIAS},
        {"label": "Goss Group", "href": None},
        {"label": "GGV", "href": "/ggv-ops-pack"},
        {"label": "Pipeline Truth", "href": None},
    ],
    "/ggv/pipeline": [
        {"label": "WOLF", "href": WOLF_ALIAS},
        {"label": "Goss Group", "href": None},
        {"label": "GGV", "href": "/ggv-ops-pack"},
        {"label": "Pipeline Truth", "href": None},
    ],
    "/ops/content-engine-live": [
        {"label": "WOLF", "href": WOLF_ALIAS},
        {"label": "Ops", "href": None},
        {"label": "Content Engine Live", "href": None},
    ],
    "/ops/conn-health-1": [
        {"label": "WOLF", "href": WOLF_ALIAS},
        {"label": "System", "href": PROGRESS_HREF},
        {"label": "Connections Health", "href": None},
    ],
    "/ops/conn-health": [
        {"label": "WOLF", "href": WOLF_ALIAS},
        {"label": "System", "href": PROGRESS_HREF},
        {"label": "Connections Health", "href": None},
    ],
    "/crm/identity-1": [
        {"label": "WOLF", "href": WOLF_ALIAS},
        {"label": "Empire", "href": EMPIRE_HREF},
        {"label": "CRM Identity", "href": "/crm-identity"},
        {"label": "Identity-1 slice", "href": None},
    ],
    "/fin/interco-1": [
        {"label": "WOLF", "href": WOLF_ALIAS},
        {"label": "Empire", "href": EMPIRE_HREF},
        {"label": "Finance", "href": None},
        {"label": "Interco-1", "href": None},
    ],
    "/fin/recon-shell-1": [
        {"label": "WOLF", "href": WOLF_ALIAS},
        {"label": "Empire", "href": EMPIRE_HREF},
        {"label": "Finance", "href": None},
        {"label": "Recon Shell-1", "href": None},
    ],
    "/fin/cash-truth-1": [
        {"label": "WOLF", "href": WOLF_ALIAS},
        {"label": "Empire", "href": EMPIRE_HREF},
        {"label": "Finance", "href": None},
        {"label": "Cash Truth-1", "href": None},
    ],
    "/fin/ap-ar-shell-1": [
        {"label": "WOLF", "href": WOLF_ALIAS},
        {"label": "Empire", "href": EMPIRE_HREF},
        {"label": "Finance", "href": None},
        {"label": "AP/AR Shell-1", "href": None},
    ],
    "/owner/needs-you-1": [
        {"label": "WOLF", "href": WOLF_ALIAS},
        {"label": "Empire", "href": EMPIRE_HREF},
        {"label": "Owner", "href": None},
        {"label": "Needs You-1", "href": None},
    ],
    "/ggv/finance/invoices": [
        {"label": "WOLF", "href": WOLF_ALIAS},
        {"label": "Goss Group", "href": None},
        {"label": "GGV", "href": "/ggv-ops-pack"},
        {"label": "Finance", "href": "/ggv/finance"},
        {"label": "Invoices", "href": None},
    ],
    "/ggv/finance/notas": [
        {"label": "WOLF", "href": WOLF_ALIAS},
        {"label": "Goss Group", "href": None},
        {"label": "GGV", "href": "/ggv-ops-pack"},
        {"label": "Finance", "href": "/ggv/finance"},
        {"label": "Notas / Bills", "href": None},
    ],
    "/ggv/finance/vendors": [
        {"label": "WOLF", "href": WOLF_ALIAS},
        {"label": "Goss Group", "href": None},
        {"label": "GGV", "href": "/ggv-ops-pack"},
        {"label": "Finance", "href": "/ggv/finance"},
        {"label": "Vendors", "href": None},
    ],
    "/ggv/finance/customers": [
        {"label": "WOLF", "href": WOLF_ALIAS},
        {"label": "Goss Group", "href": None},
        {"label": "GGV", "href": "/ggv-ops-pack"},
        {"label": "Finance", "href": "/ggv/finance"},
        {"label": "Customers", "href": None},
    ],
    "/ggv/finance/history": [
        {"label": "WOLF", "href": WOLF_ALIAS},
        {"label": "Goss Group", "href": None},
        {"label": "GGV", "href": "/ggv-ops-pack"},
        {"label": "Finance", "href": "/ggv/finance"},
        {"label": "History", "href": None},
    ],
    "/ggv/finance/reports": [
        {"label": "WOLF", "href": WOLF_ALIAS},
        {"label": "Goss Group", "href": None},
        {"label": "GGV", "href": "/ggv-ops-pack"},
        {"label": "Finance", "href": "/ggv/finance"},
        {"label": "Reports", "href": None},
    ],
    "/amg-ops-pack": [
        {"label": "WOLF", "href": WOLF_ALIAS},
        {"label": "Atrium Management", "href": None},
        {"label": "AMG", "href": None},
    ],
    "/amg-daily-ops-state": [
        {"label": "WOLF", "href": WOLF_ALIAS},
        {"label": "Atrium Management", "href": None},
        {"label": "AMG", "href": "/amg-ops-pack"},
        {"label": "Daily Ops", "href": None},
    ],
    "/amg/os-shell": [
        {"label": "WOLF", "href": WOLF_ALIAS},
        {"label": "Atrium Management", "href": None},
        {"label": "AMG", "href": "/amg-ops-pack"},
        {"label": "Operating Shell", "href": None},
    ],
    "/amg/finance": [
        {"label": "Atrium Finance", "href": None},
    ],
    "/amg/finance/ledger": [
        {"label": "Atrium Finance", "href": "/amg/finance"},
        {"label": "Ledger", "href": None},
    ],
    "/amg/finance/accounts": [
        {"label": "Atrium Finance", "href": "/amg/finance"},
        {"label": "Chart of Accounts", "href": None},
    ],
    "/amg/finance/journals": [
        {"label": "Atrium Finance", "href": "/amg/finance"},
        {"label": "Journals", "href": None},
    ],
    "/amg/finance/reports": [
        {"label": "Atrium Finance", "href": "/amg/finance"},
        {"label": "Reports", "href": None},
    ],
    "/amg/finance/approvals": [
        {"label": "Atrium Finance", "href": "/amg/finance"},
        {"label": "Approvals", "href": None},
    ],
    "/bzg": [
        {"label": "WOLF", "href": WOLF_ALIAS},
        {"label": "Blu Zone", "href": None},
    ],
    "/bzg/finance": [
        {"label": "WOLF", "href": WOLF_ALIAS},
        {"label": "Blu Zone", "href": "/bzg"},
        {"label": "Finance", "href": None},
    ],
    "/bzg/outlets": [
        {"label": "WOLF", "href": WOLF_ALIAS},
        {"label": "Blu Zone", "href": "/bzg"},
        {"label": "Outlets", "href": None},
    ],
    "/bzg/ops-desk": [
        {"label": "WOLF", "href": WOLF_ALIAS},
        {"label": "Blu Zone", "href": "/bzg"},
        {"label": "Ops Desk", "href": None},
    ],
    "/bzg/ops": [
        {"label": "WOLF", "href": WOLF_ALIAS},
        {"label": "Blu Zone", "href": "/bzg"},
        {"label": "Ops Desk", "href": None},
    ],
    "/bzg/venue-pnl": [
        {"label": "WOLF", "href": WOLF_ALIAS},
        {"label": "Blu Zone", "href": "/bzg"},
        {"label": "Venue P&L", "href": None},
    ],
    "/bzg/waste-yield": [
        {"label": "WOLF", "href": WOLF_ALIAS},
        {"label": "Blu Zone", "href": "/bzg"},
        {"label": "Waste / Yield", "href": None},
    ],
    "/bzg/waste-yield-desk": [
        {"label": "WOLF", "href": WOLF_ALIAS},
        {"label": "Blu Zone", "href": "/bzg"},
        {"label": "Waste / Yield", "href": None},
    ],
    "/bzg/labor-cost-1": [
        {"label": "WOLF", "href": WOLF_ALIAS},
        {"label": "Blu Zone", "href": "/bzg"},
        {"label": "Labor Cost", "href": None},
    ],
    "/bzg/labor-cost": [
        {"label": "WOLF", "href": WOLF_ALIAS},
        {"label": "Blu Zone", "href": "/bzg"},
        {"label": "Labor Cost", "href": None},
    ],
    "/bzg/uma-blu": [
        {"label": "WOLF", "href": WOLF_ALIAS},
        {"label": "Blu Zone", "href": "/bzg"},
        {"label": "Uma Blu", "href": "/bzg/uma-blu"},
        {"label": "Today", "href": None},
    ],
    "/bzg/uma-blu/bills": [
        {"label": "WOLF", "href": WOLF_ALIAS},
        {"label": "Blu Zone", "href": "/bzg"},
        {"label": "Uma Blu", "href": "/bzg/uma-blu"},
        {"label": "Bills", "href": None},
    ],
    "/bzg/uma-blu/issues": [
        {"label": "WOLF", "href": WOLF_ALIAS},
        {"label": "Blu Zone", "href": "/bzg"},
        {"label": "Uma Blu", "href": "/bzg/uma-blu"},
        {"label": "Issues", "href": None},
    ],
    "/bzg/uma-blu/petty": [
        {"label": "WOLF", "href": WOLF_ALIAS},
        {"label": "Blu Zone", "href": "/bzg"},
        {"label": "Uma Blu", "href": "/bzg/uma-blu"},
        {"label": "Petty", "href": None},
    ],
    "/uma-blu-close": [
        {"label": "WOLF", "href": WOLF_ALIAS},
        {"label": "Blu Zone", "href": "/bzg"},
        {"label": "Uma Blu", "href": "/bzg/uma-blu"},
        {"label": "Close", "href": None},
    ],
    INTEL_HREF: [
        {"label": "WOLF", "href": WOLF_ALIAS},
        {"label": "Intelligence", "href": None},
    ],
    CONTENT_HREF: [
        {"label": "WOLF", "href": WOLF_ALIAS},
        {"label": "Intelligence", "href": INTEL_HREF},
        {"label": "Content", "href": None},
    ],
    PROGRESS_HREF: [
        {"label": "WOLF", "href": WOLF_ALIAS},
        {"label": "System", "href": None},
        {"label": "Progress", "href": None},
    ],
    INTEGRATIONS_HREF: [
        {"label": "WOLF", "href": WOLF_ALIAS},
        {"label": "System", "href": PROGRESS_HREF},
        {"label": "Integrations", "href": None},
    ],
    SALE_HREF: [
        {"label": "WOLF", "href": WOLF_ALIAS},
        {"label": "System", "href": PROGRESS_HREF},
        {"label": "Sale", "href": None},
    ],
}

# Deny-matrix surfaces — chrome hide AND typed URL/API fail-closed (RHC V1).
DENY_MATRIX_PATHS: tuple[str, ...] = (
    PROGRESS_HREF,
    "/api/progress",
    INTEGRATIONS_HREF,
    "/api/integration-health",
    SALE_HREF,
    "/api/sale-evidence-pack",
    EMPIRE_HREF,
    WOLF_ALIAS,
    "/api/owner/empire-pack",
    "/bzg",
    "/bzg/uma-blu",
    "/ggv-ops-pack",
    "/amg-ops-pack",
    INTEL_HREF,
    CONTENT_HREF,
)

HONESTY_BASE: dict[str, Any] = {
    "bound": BOUND,
    "slice": SLICE,
    "schema": SCHEMA_ID,
    "additive_only": True,
    "invented_proven": False,
    "invented_ready": False,
    "hidden_ne_permission": True,
    "api_auth_canonical": True,
    "second_boards_menu": False,
    "owner_landing_empire": True,
    "devi_landing_uma_today": True,
    "amanda_landing_ggv_overview": True,
    "coral_landing_amg_today": False,
    "haikal_landing_content": True,
    "intel_home_soft_land": True,
    "content_under_intelligence": True,
    "progress_under_system_only": True,
    "system_home_soft_land_progress": True,
    "sale_under_system": True,
    "factory_grammar_empty": True,
    "staff_hide_system_admin": True,
    "wolf_alias_empire": True,
    "hierarchy_breadcrumbs": True,
    "bzg_crumbs_wolf_blu_uma_today": True,
    "ggv_crumbs_wolf_goss_ggv": True,
    "amg_crumbs_wolf_atrium_amg": True,
    "intel_crumbs_wolf_intelligence": True,
    "system_crumbs_wolf_system": True,
    "specialist_not_primary": True,
    "specialist_soft_redirect_empire": True,
    "grammar_empty_honest": True,
    "amg_finance_nested_visible_only": True,
    "legacy_uma_alias": True,
    "client_projection_fail_closed": True,
    "direction_up_back_home": True,
    "context_switcher_multi_only": True,
    "responsive_tokens_media": True,
    "responsive_shell_v1_prove": True,
    "deny_matrix_expanded": True,
    "v1_ready_requires": list(V1_READY_REQUIRES),
    "permissions_audience_prove": True,
    "four_layer_permissions": True,
    "person_role_assignment_scope_permission_audience": True,
    "sample_surfaces_empire_uma_progress": True,
    "route_merge_retire_redirect": True,
    "redirect_gt_delete": True,
    "mgmt_cluster_soft_land_bu": True,
    "radar_soft_land_empire_priorities": True,
    "dashboards_html_to_clean": True,
    "content_brand_peers_to_content": True,
    "active_packs_not_killed": True,
    "nas_library_upload_p0": True,
    "nas_index_continue": True,
    "nas_index_operator_depth": True,
    "nas_canonical_media": True,
    "ggv_content_nas_haikal_prep": True,
    "ggv_content_ops_depth": True,
    "amg_day_ops_operator_depth": True,
    "amg_packages_operator_depth": True,
    "amg_revenue_yield_operator_depth": True,
    "amg_journey_operator_depth": True,
    "amg_sla_incident_operator_depth": True,
    "amg_service_improve_operator_depth": True,
    "ggv_client_profitability_operator_depth": True,
    "ggv_intercompany_client_operator_depth": True,
    "owner_progress_needs_you_depth": True,
    "staff_ops_needs_you_connective": True,
    "ggv_ops_needs_you_connective": True,
    "amg_ops_needs_you_connective": True,
    "intel_ops_needs_you_connective": True,
    "bzg_ops_needs_you_connective": True,
    "crm_ops_needs_you_connective": True,
    "crm_identity_operator_depth": True,
    "crm_package_intel_operator_depth": True,
    "sale_ops_needs_you_connective": True,
    "intg_ops_needs_you_connective": True,
    "msc_ops_needs_you_connective": True,
    "msc_asset_operator_depth": True,
    "msc_compliance_operator_depth": True,
    "owner_commissioning_operator_depth": True,
    "strat_ops_needs_you_connective": True,
    "dr_ops_needs_you_connective": True,
    "core_ops_needs_you_connective": True,
    "haikal_nas_operator_path": True,
    "invented_haikal_human_pass": False,
    "full_tree_indexed": False,
    "staff_ready": False,
    "money": None,
    "production_mutate": False,
    "cloudflare_mutated": False,
}

# Back-compat alias — prefer honesty_flags() which merges live V1 gate status.
HONESTY: dict[str, Any] = dict(HONESTY_BASE, proven=False, ready=False)


class WolfShellError(ValueError):
    def __init__(self, message: str, *, code: str = "invalid") -> None:
        super().__init__(message)
        self.code = code


def _evidence_pngs(*, prefix: str = "") -> list[str]:
    if not EVIDENCE_DIR.is_dir():
        return []
    out: list[str] = []
    for p in sorted(EVIDENCE_DIR.glob("*.png")):
        name = p.name.lower()
        if prefix and prefix not in name:
            continue
        out.append(str(p.relative_to(EVIDENCE_DIR.parent.parent.parent)))
    return out


def _debt_registered() -> bool:
    debt = EVIDENCE_DIR / "DEBT.md"
    return debt.is_file() and debt.stat().st_size > 20


def v1_gates_status() -> dict[str, dict[str, Any]]:
    """Six V1 READY bars — evidence files OR explicit DEBT for screenshots.

    Automated bars (role/deny/breadcrumb/context) are marked met when the
    prove test suite writes MARKERS; until then they stay unmet here so
    whoami never invents READY. Screenshots/DEBT are filesystem-visible.
    """
    desktop = _evidence_pngs(prefix="desktop")
    mobile = _evidence_pngs(prefix="mobile")
    debt = _debt_registered()
    markers_path = EVIDENCE_DIR / "AUTOMATED_MARKERS.json"
    markers: dict[str, Any] = {}
    if markers_path.is_file():
        try:
            markers = json.loads(markers_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            markers = {}

    def auto(key: str) -> dict[str, Any]:
        met = bool(markers.get(key))
        return {
            "met": met,
            "real_evidence": met,
            "via_debt": False,
            "evidence": markers.get(f"{key}_evidence") or ("automated" if met else None),
        }

    return {
        "desktop_screenshots": {
            "met": bool(desktop) or debt,
            "real_evidence": bool(desktop),
            "via_debt": debt and not desktop,
            "evidence": desktop or ("DEBT.md" if debt else None),
        },
        "mobile_screenshots": {
            "met": bool(mobile) or debt,
            "real_evidence": bool(mobile),
            "via_debt": debt and not mobile,
            "evidence": mobile or ("DEBT.md" if debt else None),
        },
        "role_matrix_proof": auto("role_matrix_proof"),
        "url_api_denial_proof": auto("url_api_denial_proof"),
        "breadcrumb_back_up_proof": auto("breadcrumb_back_up_proof"),
        "context_switch_proof": auto("context_switch_proof"),
    }


def v1_all_bars_met() -> bool:
    return all(bool(g.get("met")) for g in v1_gates_status().values())


def v1_all_real_evidence() -> bool:
    """READY notify eligibility — DEBT alone does not invent READY."""
    return all(bool(g.get("real_evidence")) for g in v1_gates_status().values())


def deny_matrix_paths() -> list[str]:
    return list(DENY_MATRIX_PATHS)


def role_matrix_fixtures() -> dict[str, dict[str, Any]]:
    """Person→Audience fixtures for clearance prove (chrome visibility map)."""
    return {
        "matt": {
            "person_id": "PERS-MATT",
            "email": "mrwolf@wolfcommand.net",
            "audience": "OWNER",
            "landing": WOLF_ALIAS,
            "must_see_sections": ["home", "businesses", "intelligence", "system"],
            "must_hide_hrefs": [],
            "context_switcher": True,
        },
        "devi": {
            "person_id": "PERS-DEVI",
            "email": "deviputu236@gmail.com",
            "audience": "OPERATOR",
            "landing": "/bzg/uma-blu",
            "must_see_sections": ["home", "businesses"],
            "must_hide_hrefs": [PROGRESS_HREF, INTEGRATIONS_HREF, SALE_HREF, EMPIRE_HREF],
            "context_switcher": False,
        },
        "haikal": {
            "person_id": "PERS-HAIKAL",
            "email": "haikalqilbari123@gmail.com",
            "audience": "SPECIALIST_CONTENT",
            "landing": CONTENT_HREF,
            "must_see_sections": ["home", "businesses", "intelligence"],
            "must_hide_hrefs": [PROGRESS_HREF, INTEGRATIONS_HREF, SALE_HREF, INTEL_HREF],
            "context_switcher": False,
        },
        "client": {
            "person_id": None,
            "email": None,
            "audience": "CLIENT",
            "landing": None,
            "must_see_sections": [],
            "must_hide_hrefs": list(ALL_HREFS),
            "context_switcher": False,
        },
        "unauth": {
            "person_id": None,
            "email": None,
            "audience": "CLIENT",
            "landing": None,
            "must_see_sections": [],
            "must_hide_hrefs": list(ALL_HREFS),
            "context_switcher": False,
        },
    }


def honesty_flags() -> dict[str, Any]:
    flags = dict(HONESTY_BASE)
    gates = v1_gates_status()
    # Never invent CAP PROVEN/READY in honesty (soft Wave1–8 assert ready=false).
    # Owner READY notify eligibility is a separate gate flag — not invented CAP READY.
    flags["proven"] = False
    flags["ready"] = False
    flags["v1_gates"] = gates
    flags["v1_all_bars_met"] = bool(v1_all_bars_met())
    flags["v1_ready_notify_eligible"] = bool(v1_all_real_evidence())
    # Keep module-level HONESTY mirror current for legacy readers.
    HONESTY.clear()
    HONESTY.update(flags)
    return flags


def ia_tree() -> list[dict[str, Any]]:
    return [dict(sec, items=[dict(it) for it in sec["items"]]) for sec in IA_TREE]


def specialist_soft_redirect_target(path: str | None) -> str | None:
    """Return Empire soft-land target when path is a retired specialist primary entry."""
    p = _norm_path(path)
    raw = (path or "").split("?")[0].split("#")[0]
    if not raw.startswith("/"):
        raw = "/" + raw
    candidates = {p, raw, raw.rstrip("/") or "/", (raw.rstrip("/") or "/") + ".html"}
    # Also accept /dashboards/<slug>.html forms already enumerated.
    if any(c in SPECIALIST_SOFT_REDIRECT_PATHS for c in candidates):
        return SPECIALIST_SOFT_REDIRECT_TARGET
    # Slug match on final path segment (no new sprawl invent).
    slug = p.rsplit("/", 1)[-1].lower().removesuffix(".html")
    if slug in SPECIALIST_PRIMARY_SLUGS:
        return SPECIALIST_SOFT_REDIRECT_TARGET
    return None


def primary_ia_specialist_leaks(tree: list[dict[str, Any]] | None = None) -> list[str]:
    """Return specialist slugs/keys found in primary IA (must be empty)."""
    tree = tree if tree is not None else IA_TREE
    leaks: list[str] = []
    for sec in tree:
        for it in sec.get("items") or []:
            key = str(it.get("key") or "").lower()
            href = str(it.get("href") or "").lower()
            title = str(it.get("title") or "").lower()
            slug = href.rsplit("/", 1)[-1].removesuffix(".html")
            if (
                key in SPECIALIST_PRIMARY_KEYS
                or slug in SPECIALIST_PRIMARY_SLUGS
                or any(s in title for s in SPECIALIST_PRIMARY_SLUGS)
            ):
                leaks.append(key or slug or title)
    return leaks


def specialist_not_in_primary_ia(tree: list[dict[str, Any]] | None = None) -> bool:
    return len(primary_ia_specialist_leaks(tree)) == 0


# Primary seat wins over the old person fixture map for these jobs.
_ASSIGNMENT_AUDIENCE_ROLES = frozenset(
    {
        "ROLE-GGV-CREATIVE-DIRECTOR",
        "ROLE-CONTENT-CREATOR",
        "ROLE-GGV-EXTERNAL-ACCOUNTANT",
        "ROLE-AMG-FINANCE-OFFICER",
        "ROLE-AMG-FINANCIAL-CONTROLLER",
        "ROLE-AMG-ACCOUNTS-PAYABLE",
        "ROLE-AMG-ACCOUNTS-RECEIVABLE",
        "ROLE-AMG-EXTERNAL-ACCOUNTANT",
        "ROLE-BZG-FINANCIAL-CONTROLLER",
        "ROLE-BZG-EXTERNAL-ACCOUNTANT",
    }
)


def audience_for_person(person_id: str | None) -> str:
    if not person_id:
        return "CLIENT"
    pid = str(person_id)
    rows = _org_assignments(pid)
    if rows:
        primary = [
            row for row in rows
            if int(row.get("is_primary") or 0) == 1
            and str(row.get("role") or "") in _ASSIGNMENT_AUDIENCE_ROLES
        ]
        chosen = primary[0] if primary else rows[0]
        role = str(chosen.get("role") or "")
        if role in _ASSIGNMENT_AUDIENCE_ROLES and role in ROLE_AUDIENCE:
            return ROLE_AUDIENCE[role]
    mapped = PERSON_AUDIENCE.get(pid)
    if mapped:
        return mapped
    if not rows:
        return "CLIENT"
    role = str(rows[0].get("role") or "")
    if role in ROLE_AUDIENCE:
        return ROLE_AUDIENCE[role]
    label = str(rows[0].get("label") or "").lower()
    if "owner" in label and "executive" in label:
        return "OWNER"
    return "CLIENT"


def pages_for_audience(audience: str) -> list[str]:
    return list(AUDIENCE_PAGES.get(audience, []))


def landing_for_audience(audience: str) -> str | None:
    return LANDING_BY_AUDIENCE.get(audience)


def is_empire_path(path: str | None) -> bool:
    p = (path or "").split("?")[0].split("#")[0].rstrip("/") or "/"
    if not p.startswith("/"):
        p = "/" + p
    return p.lower() in {a.lower() for a in EMPIRE_ALIASES}


def home_primary_href() -> str:
    """HOME primary destination for Owner chrome (Empire Pulse)."""
    home = next((s for s in IA_TREE if s["id"] == "home"), None)
    if not home:
        return EMPIRE_HREF
    for it in home["items"]:
        if it.get("primary") or it.get("key") == "empire":
            return str(it["href"])
    return EMPIRE_HREF


def progress_section_id() -> str | None:
    for sec in IA_TREE:
        for it in sec["items"]:
            if it.get("href") == PROGRESS_HREF or it.get("key") == "progress":
                return str(sec["id"])
    return None


def _norm_path(path: str | None) -> str:
    p = (path or "").split("?")[0].split("#")[0].rstrip("/") or "/"
    if not p.startswith("/"):
        p = "/" + p
    return p.lower()


_CATALOG_DB = Path(__file__).resolve().parents[2] / "catalog" / "content_library.sqlite"
_ROLE_HREF: dict[str, str] = {
    "ROLE-GGV-CREATIVE-DIRECTOR": CONTENT_HREF,
    "ROLE-CONTENT": CONTENT_HREF,
    "ROLE-CONTENT-MGMT": CONTENT_HREF,
    "ROLE-CONTENT-CREW": CONTENT_HREF,
    "ROLE-CONTENT-CREATOR": CONTENT_HREF,
    "ROLE-BZG-FB-OPS-LEAD": "/bzg/uma-blu",
    "ROLE-BZG-HEAD-CHEF": "/bzg/recipe-builder",
    "ROLE-GGV-LEAD": "/ggv-ops-pack",
    "ROLE-AMG-OPS": "/amg-ops-pack",
    "ROLE-AMG-GM": "/amg-ops-pack",
    "ROLE-MATT": WOLF_ALIAS,
    "ROLE-OWNER": WOLF_ALIAS,
    "ROLE-AMG-FINANCE-OFFICER": "/amg/finance",
    "ROLE-AMG-FINANCIAL-CONTROLLER": "/amg/finance",
    "ROLE-AMG-ACCOUNTS-PAYABLE": "/amg/finance",
    "ROLE-AMG-ACCOUNTS-RECEIVABLE": "/amg/finance",
    "ROLE-AMG-EXTERNAL-ACCOUNTANT": "/amg/finance",
    "ROLE-BZG-FINANCIAL-CONTROLLER": "/bzg/finance",
    "ROLE-BZG-EXTERNAL-ACCOUNTANT": "/bzg/finance",
    "ROLE-GGV-FINANCE-OPERATOR": "/ggv/finance",
    "ROLE-GGV-EXTERNAL-ACCOUNTANT": "/ggv/finance",
}


def _seed_assignments(person_id: str | None) -> list[dict[str, Any]]:
    if not person_id:
        return []
    return [dict(a) for a in PERSON_ASSIGNMENTS.get(str(person_id), [])]


def _org_assignments(person_id: str) -> list[dict[str, Any]]:
    """Active org_assignments for this person. Seed fixtures are not a substitute."""
    if not _CATALOG_DB.is_file():
        return []
    try:
        from core import content_engine_repair as repair

        conn = sqlite3.connect(str(_CATALOG_DB))
        conn.row_factory = sqlite3.Row
    except sqlite3.Error:
        return []
    try:
        try:
            repair.ensure_content_all_brands_scope(conn)
        except Exception:
            pass
        rows = conn.execute(
            """
            SELECT a.assignment_id, a.is_primary, a.position_id,
                   p.role_id, p.position_label, r.display_name AS role_label
            FROM org_assignments a
            JOIN org_positions p ON p.position_id = a.position_id
            JOIN org_roles r ON r.role_id = p.role_id
            WHERE a.person_id = ?
              AND a.status = 'ACTIVE'
              AND a.end_at IS NULL
            ORDER BY a.is_primary DESC, a.assignment_id
            """,
            (person_id,),
        ).fetchall()
        seed_href = ""
        seed = _seed_assignments(person_id)
        if seed:
            seed_href = str(seed[0].get("href") or "")
        out: list[dict[str, Any]] = []
        for row in rows:
            scopes = [
                str(r["scope_id"])
                for r in conn.execute(
                    """
                    SELECT scope_id FROM org_assignment_scopes
                    WHERE assignment_id = ?
                      AND status = 'ACTIVE'
                      AND end_at IS NULL
                    ORDER BY scope_id
                    """,
                    (row["assignment_id"],),
                ).fetchall()
                if r["scope_id"]
            ]
            role = str(row["role_id"] or "")
            href = _ROLE_HREF.get(role) or seed_href
            out.append(
                {
                    "id": row["assignment_id"],
                    "role": role,
                    "label": row["role_label"] or row["position_label"] or role,
                    "scope": scopes[0] if scopes else "",
                    "scopes": scopes,
                    "href": href,
                    "position_id": row["position_id"],
                    "is_primary": int(row["is_primary"] or 0),
                    "source": "org_assignments",
                }
            )
        return out
    except sqlite3.Error:
        return []
    finally:
        conn.close()


def assignments_for_person(person_id: str | None) -> list[dict[str, Any]]:
    """Real ACTIVE org assignments when the catalog has them. Seed is the fallback."""
    if not person_id:
        return []
    seed = _seed_assignments(person_id)
    db = _org_assignments(str(person_id))
    if not db:
        return seed
    extra: list[str] = []
    seen: set[str] = set()
    for scope in scopes_from_assignments(seed):
        if scope not in seen:
            seen.add(scope)
            extra.append(scope)
    primary = db[0]
    have = [str(s) for s in (primary.get("scopes") or []) if str(s).strip()]
    have_set = set(have)
    for scope in extra:
        if scope not in have_set:
            have.append(scope)
            have_set.add(scope)
    primary["scopes"] = have
    if have and not primary.get("scope"):
        primary["scope"] = have[0]
    return db


def roles_from_assignments(assignments: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for a in assignments:
        role = str(a.get("role") or "").strip()
        if role and role not in seen:
            seen.add(role)
            out.append(role)
    return out


def scopes_from_assignments(assignments: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for a in assignments:
        values: list[Any] = []
        if a.get("scope"):
            values.append(a.get("scope"))
        values.extend(a.get("scopes") or [])
        for raw in values:
            scope = str(raw or "").strip()
            if scope and scope not in seen:
                seen.add(scope)
                out.append(scope)
    return out


def layers_union_for_roles(roles: list[str]) -> dict[str, dict[str, bool]]:
    """Union ROLE_SURFACE_LAYERS across roles → surface → layer bool map."""
    granted: dict[str, set[str]] = {sid: set() for sid in SAMPLE_SURFACES}
    for role in roles:
        table = ROLE_SURFACE_LAYERS.get(role) or _EMPTY_SAMPLE
        for sid in SAMPLE_SURFACES:
            granted[sid] |= set(table.get(sid) or frozenset())
    out: dict[str, dict[str, bool]] = {}
    for sid in SAMPLE_SURFACES:
        out[sid] = {layer: layer in granted[sid] for layer in PERM_LAYERS}
    return out


def surface_layers_for_whoami(whoami: dict[str, Any] | None) -> dict[str, dict[str, bool]]:
    if not whoami:
        return layers_union_for_roles([])
    if whoami.get("wolf_authorized") is True or whoami.get("audience") == "OWNER":
        return layers_union_for_roles(["ROLE-OWNER"])
    roles = list(whoami.get("roles") or [])
    if not roles:
        roles = roles_from_assignments(list(whoami.get("assignments") or []))
    return layers_union_for_roles(roles)


def can_layer(
    whoami: dict[str, Any] | None,
    surface: str,
    layer: str,
) -> bool:
    """True when identity holds the named layer on a sample surface."""
    surfaces = surface_layers_for_whoami(whoami)
    row = surfaces.get(surface) or {}
    return bool(row.get(layer))


def permission_chain(whoami: dict[str, Any] | None) -> dict[str, Any]:
    """Person→Role→Assignment→Scope→Permission→Audience projection for chrome."""
    who = whoami or {}
    asg = list(who.get("assignments") or [])
    roles = list(who.get("roles") or roles_from_assignments(asg))
    surfaces = surface_layers_for_whoami(who)
    return {
        "person_id": who.get("person_id"),
        "roles": roles,
        "assignments": asg,
        "scopes": scopes_from_assignments(asg),
        "permissions": {
            "layers": list(PERM_LAYERS),
            "surfaces": surfaces,
        },
        "audience": who.get("audience"),
    }


def filter_assignments(
    assignments: list[dict[str, Any]],
    whoami: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Keep only assignments whose href the identity may navigate."""
    if not assignments:
        return []
    if whoami and (
        whoami.get("wolf_authorized") is True or whoami.get("audience") == "OWNER"
    ):
        return [dict(a) for a in assignments]
    allowed = set(filter_hrefs(whoami))
    # Specialist landings (Atrium / BZG / GGV finance, My Work) may sit outside
    # primary IA ALL_HREFS — still honour audience pages so multi-entity seats
    # are not collapsed to the one href that happens to be in IA_TREE.
    for page in whoami.get("pages") or [] if whoami else []:
        allowed.add(_norm_path(str(page)))
    # Empire alias: /wolf allowed when empire pack is
    if EMPIRE_HREF in allowed:
        allowed |= set(EMPIRE_ALIASES)
    out: list[dict[str, Any]] = []
    for a in assignments:
        href = _norm_path(str(a.get("href") or ""))
        if href in allowed or href in { _norm_path(x) for x in allowed }:
            out.append(dict(a))
        elif is_empire_path(href) and (EMPIRE_HREF in allowed or any(is_empire_path(x) for x in allowed)):
            out.append(dict(a))
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for item in out:
        href = _norm_path(str(item.get("href") or ""))
        if href in seen:
            continue
        seen.add(href)
        deduped.append(item)
    return deduped


def breadcrumbs_for_path(
    path: str | None,
    whoami: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Hierarchy crumbs. Filter link targets to authorised destinations only."""
    p = _norm_path(path)
    trail = ROUTE_CRUMBS.get(p)
    if not trail and is_empire_path(p):
        trail = ROUTE_CRUMBS[EMPIRE_HREF]
    if not trail:
        return [{"label": "Here", "href": None}]
    allowed = set(filter_hrefs(whoami)) if whoami else set()
    if whoami and (
        whoami.get("wolf_authorized") is True or whoami.get("audience") == "OWNER"
    ):
        allowed = set(ALL_HREFS) | set(EMPIRE_ALIASES)
    elif EMPIRE_HREF in allowed:
        allowed |= set(EMPIRE_ALIASES)
    landing = (whoami or {}).get("landing")
    out: list[dict[str, Any]] = []
    for crumb in trail:
        c = dict(crumb)
        href = c.get("href")
        if href:
            nh = _norm_path(str(href))
            ok = False
            if not allowed:
                ok = False
            elif nh in {_norm_path(x) for x in allowed} or is_empire_path(nh) and any(
                is_empire_path(x) for x in allowed
            ):
                ok = True
            if not ok:
                # Soft-land WOLF/HOME crumb for scoped users onto their landing
                if c.get("label") in ("HOME", "WOLF") and landing:
                    c["href"] = landing
                else:
                    c["href"] = None
        out.append(c)
    return out


def bzg_grammar() -> list[dict[str, Any]]:
    return [dict(g) for g in BZG_GRAMMAR]


def uma_grammar() -> list[dict[str, Any]]:
    return [dict(g) for g in UMA_GRAMMAR]


def ggv_grammar() -> list[dict[str, Any]]:
    return [dict(g) for g in GGV_GRAMMAR]


def amg_grammar() -> list[dict[str, Any]]:
    return [dict(g) for g in AMG_GRAMMAR]


def intel_grammar() -> list[dict[str, Any]]:
    return [dict(g) for g in INTEL_GRAMMAR]


def system_grammar() -> list[dict[str, Any]]:
    return [dict(g) for g in SYSTEM_GRAMMAR]


def grammar_has_fake_pct(items: list[dict[str, Any]] | None = None) -> bool:
    """True if any grammar label invents a fake percentage — must stay False."""
    for g in items or (
        BZG_GRAMMAR
        + UMA_GRAMMAR
        + GGV_GRAMMAR
        + AMG_GRAMMAR
        + INTEL_GRAMMAR
        + SYSTEM_GRAMMAR
    ):
        label = str(g.get("label") or "")
        state = str(g.get("state") or "")
        if "%" in label or "%" in state:
            return True
        if state.upper() not in {"LIVE", "EMPTY"} and g.get("href"):
            # live must be explicit; unknown non-empty states are not % but flag invent
            pass
    return False


def parent_for_path(
    path: str | None,
    whoami: dict[str, Any] | None = None,
) -> str | None:
    """UP target — parent level when authorised; else authorised landing/HOME."""
    p = _norm_path(path)
    parent = ROUTE_PARENT.get(p)
    if parent is None and is_empire_path(p):
        return None
    if parent is None:
        return (whoami or {}).get("landing") or (whoami or {}).get("home_primary")
    allowed = set(filter_hrefs(whoami)) if whoami else set()
    if whoami and (
        whoami.get("wolf_authorized") is True or whoami.get("audience") == "OWNER"
    ):
        return parent
    np = _norm_path(parent)
    if np in {_norm_path(x) for x in allowed} or (
        is_empire_path(np) and any(is_empire_path(x) for x in allowed)
    ):
        return parent
    return (whoami or {}).get("landing") or (whoami or {}).get("home_primary")


def home_href_for_whoami(whoami: dict[str, Any] | None) -> str | None:
    if not whoami:
        return None
    return whoami.get("landing") or whoami.get("home_primary")


def direction_for_path(
    path: str | None,
    whoami: dict[str, Any] | None = None,
    *,
    back_href: str | None = None,
) -> dict[str, Any]:
    """Explicit UP / BACK / HOME — Wolf must not depend on browser-back."""
    up = parent_for_path(path, whoami)
    home = home_href_for_whoami(whoami)
    back = back_href
    if back:
        nb = _norm_path(back)
        allowed = set(filter_hrefs(whoami)) if whoami else set()
        if whoami and (
            whoami.get("wolf_authorized") is True or whoami.get("audience") == "OWNER"
        ):
            allowed = set(ALL_HREFS) | set(EMPIRE_ALIASES)
        elif EMPIRE_HREF in allowed:
            allowed |= set(EMPIRE_ALIASES)
        if nb not in {_norm_path(x) for x in allowed} and not (
            is_empire_path(nb) and any(is_empire_path(x) for x in allowed)
        ):
            back = up or home
    else:
        back = up or home
    return {
        "up": up,
        "back": back,
        "home": home,
        # FORWARD/NEXT only when product warrants + authorised — V1 honest None.
        "next": None,
    }


def _hello_for(person_id: str | None, audience: str) -> str:
    mapped = PERSON_HELLO.get(str(person_id or ""))
    if mapped:
        return mapped
    if person_id:
        try:
            from core import identity as _identity

            person = _identity.get_person(person_id)
            name = str((person or {}).get("display_name") or "").strip()
            if name:
                return name
        except Exception:
            pass
    return audience


def build_whoami(
    *,
    person_id: str | None = None,
    email: str | None = None,
    audience: str | None = None,
    active_assignment_id: str | None = None,
) -> dict[str, Any]:
    """Chrome visibility projection only. Not an auth grant.

    Wires Person→Role→Assignment→Scope→Permission→Audience for shell whoami/nav.
    """
    aud = audience or audience_for_person(person_id)
    pages = pages_for_audience(aud)
    owner = aud in {"OWNER", "SYSTEM"}
    landing = landing_for_audience(aud)
    home_primary = home_primary_href() if EMPIRE_HREF in pages or owner else None
    base = {
        "ok": True,
        "person_id": person_id,
        "email": email,
        "audience": aud,
        "role_label": aud,
        "hello": _hello_for(person_id, aud),
        "wolf_authorized": owner,
        "scoped": not owner,
        "pages": pages,
        "landing": landing,
        "home_primary": home_primary,
        "home_primary_key": "empire" if home_primary else None,
        "hidden_ne_permission": True,
        "api_auth_canonical": True,
        "bound": BOUND,
        "slice": SLICE,
    }
    raw_asg = assignments_for_person(person_id)
    asg = filter_assignments(raw_asg, base)
    if not asg and raw_asg:
        asg = raw_asg
    active = None
    if active_assignment_id:
        active = next((a for a in asg if a.get("id") == active_assignment_id), None)
    if active is None and asg:
        active = asg[0]
    roles = roles_from_assignments(asg)
    if owner and "ROLE-OWNER" not in roles:
        roles = ["ROLE-OWNER"] + roles
    base["assignments"] = asg
    base["active_assignment_id"] = (active or {}).get("id")
    base["active_assignment"] = dict(active) if active else None
    base["context_switcher"] = len(asg) > 1
    base["roles"] = roles
    # Scopes come from the assignment rows, including ones the chrome filter hid.
    base["scopes"] = scopes_from_assignments(raw_asg)
    surfaces = layers_union_for_roles(roles if roles else [])
    if owner:
        surfaces = layers_union_for_roles(["ROLE-OWNER"])
    base["permissions"] = {
        "layers": list(PERM_LAYERS),
        "surfaces": surfaces,
    }
    base["chain"] = permission_chain(base)
    return base


def filter_hrefs(whoami: dict[str, Any] | None) -> list[str]:
    if not whoami:
        return []
    if whoami.get("wolf_authorized") is True or whoami.get("audience") == "OWNER":
        return list(ALL_HREFS)
    pages = whoami.get("pages")
    if not isinstance(pages, list):
        return []
    allowed = {str(p) for p in pages}
    return [h for h in ALL_HREFS if h in allowed]


def filter_ia_tree(whoami: dict[str, Any] | None) -> list[dict[str, Any]]:
    allowed = set(filter_hrefs(whoami))
    out: list[dict[str, Any]] = []
    for sec in IA_TREE:
        kids = [dict(it) for it in sec["items"] if it["href"] in allowed]
        if kids:
            out.append({"id": sec["id"], "title": sec["title"], "items": kids})
    return out


def whoami_from_identity(identity: dict[str, Any] | None) -> dict[str, Any]:
    if not identity or not identity.get("ok"):
        return build_whoami(person_id=None, email=None, audience="CLIENT")
    return build_whoami(
        person_id=identity.get("person_id"),
        email=identity.get("email") or identity.get("permission_subject"),
    )


def shell_whoami_payload(identity: dict[str, Any] | None) -> dict[str, Any]:
    who = whoami_from_identity(identity)
    return {
        "ok": True,
        "whoami": who,
        "ia": filter_ia_tree(who),
        "home_primary": who.get("home_primary"),
        "landing": who.get("landing"),
        "assignments": who.get("assignments") or [],
        "context_switcher": bool(who.get("context_switcher")),
        "chain": who.get("chain") or permission_chain(who),
        "permissions": who.get("permissions"),
        "honesty": honesty_flags(),
    }


_SKIP_REL_PREFIXES = ("deliveries/", "sops/", "content-manuals/")


def should_inject(rel: str) -> bool:
    rel = (rel or "").lstrip("/")
    if not rel.endswith(".html"):
        return False
    for p in _SKIP_REL_PREFIXES:
        if rel.startswith(p):
            return False
    return True


_NAV_STUB = (
    b'<nav id="wolfnav" aria-label="Wolf global navigation">'
    b'<div class="nv-row">'
    b'<button type="button" id="wolfnav-t" aria-label="Boards" '
    b'aria-expanded="false" aria-controls="wolf-boards">Boards</button>'
    b'<div class="nv-brand" id="wolfnav-brand"><b>Wolf</b></div>'
    b'<div class="nv-dir" id="wolfnav-dir" role="group" aria-label="Direction">'
    b'<a class="nv-dir-btn" id="wolfnav-up" href="#" data-wolf-dir="up">Up</a>'
    b'<a class="nv-dir-btn" id="wolfnav-back" href="#" data-wolf-dir="back">Back</a>'
    b'<a class="nv-dir-btn" id="wolfnav-home" href="#" data-wolf-dir="home">Home</a>'
    b"</div>"
    b'<nav class="nv-crumbs" id="wolfnav-crumbs" aria-label="Breadcrumb"></nav>'
    b'<div class="nv-ctx" id="wolfnav-ctx" hidden></div>'
    b'<div class="nv-hello" id="wolfnav-hello"></div>'
    b'<div class="nv-footer"><a href="/signout" title="End session">Sign out</a></div>'
    b"</div>"
    b'<div id="wolf-boards" role="menu"></div>'
    b"</nav>"
    b'<div id="wolfnav-scrim"></div>'
)


_CONTENT_DESK_RELS = frozenset({"content-2.0.html", "content-2.0"})
_CONTENT_ENG_GRAMMAR_KEYS = frozenset({"decision", "akr"})
_STAFF_OMIT_ENG_RE = re.compile(
    r"<!--STAFF_OMIT_ENG-->.*?<!--/STAFF_OMIT_ENG-->",
    re.DOTALL,
)
# Content Engine Wolf Intelligence is scaffolding. Hide it from the staff nav
# until it is the canonical Wolf Intelligence with the same ACL. Owner keeps it.
_STAFF_WI_NAV_RE = re.compile(
    r"\s*<button\b[^>]*\bstaff-wi-nav\b[^>]*>.*?</button>",
    re.IGNORECASE | re.DOTALL,
)
# Dev identity, raw subject, and other engineering chrome. Owner file keeps them.
_STAFF_ENG_CHROME_RE = re.compile(
    r"\s*<(span|label|select|div|a|p)\b[^>]*\bstaff-eng-chrome\b[^>]*>.*?</\1>",
    re.IGNORECASE | re.DOTALL,
)
_STAFF_WI_SECTION_RE = re.compile(
    r"\s*<!-- WOLF INTELLIGENCE -->\s*<section\b[^>]*\bid=\"view-wolf\"[^>]*>.*?</section>",
    re.IGNORECASE | re.DOTALL,
)


def content_desk_rel(rel: str | None) -> bool:
    return (rel or "").lstrip("/") in _CONTENT_DESK_RELS


def content_staff_audience(whoami: dict[str, Any] | None) -> bool:
    """Staff Content desk. Owner and SYSTEM may keep engineering chrome."""
    aud = str((whoami or {}).get("audience") or "")
    return aud not in {"OWNER", "SYSTEM"}


def intel_grammar_for_audience(
    whoami: dict[str, Any] | None = None,
    *,
    rel: str = "",
) -> list[dict[str, Any]]:
    """Content staff desk omits Decision Memory and AKR. Other intel pages keep them."""
    items = intel_grammar()
    if content_desk_rel(rel) and content_staff_audience(whoami):
        return [g for g in items if g.get("key") not in _CONTENT_ENG_GRAMMAR_KEYS]
    return items


def apply_content_staff_desk(
    raw: bytes,
    *,
    rel: str = "",
    whoami: dict[str, Any] | None = None,
) -> bytes:
    """Strip engineering-only Content blocks for the staff audience. No maturity invent."""
    if not content_desk_rel(rel) or not content_staff_audience(whoami):
        return raw
    text = raw.decode("utf-8", "replace")
    text = _STAFF_OMIT_ENG_RE.sub("", text)
    text = _STAFF_WI_NAV_RE.sub("", text)
    text = _STAFF_WI_SECTION_RE.sub("", text)
    text = _STAFF_ENG_CHROME_RE.sub("", text)
    text = text.replace(
        'class="staff-content-desk"',
        'class="staff-content-desk ce-staff-shell"',
        1,
    )
    return text.encode("utf-8")


def inject_shell(
    raw: bytes,
    *,
    rel: str = "",
    whoami: dict[str, Any] | None = None,
) -> bytes:
    """Additive inject: tokens + shell CSS + whoami bake + #wolfnav stub + sidenav.js.

    Idempotent: skips if #wolfnav or sidenav.js already present.
    Never invents a second Boards menu.
    Staff Content (/content-2.0) drops engineering-only blocks for non-owner audiences.
    """
    if not should_inject(rel):
        return raw
    raw = apply_content_staff_desk(raw, rel=rel, whoami=whoami)
    staff_ce = content_desk_rel(rel) and content_staff_audience(whoami)
    lower = raw.lower()
    out = raw

    head_bits: list[bytes] = []
    if b"wolf-tokens.css" not in lower:
        head_bits.append(
            f'<link rel="stylesheet" href="/wolf-tokens.css?v={CACHE_TOKEN}">'.encode()
        )
    if b"wolf-shell.css" not in lower:
        head_bits.append(
            f'<link rel="stylesheet" href="/assets/wolf-shell.css?v={CACHE_TOKEN}">'.encode()
        )
    if b"window.__WOLF_WHOAMI__" not in lower and whoami is not None:
        payload = json.dumps(whoami, separators=(",", ":"), default=str)
        # Escape </script> breakouts
        payload = payload.replace("<", "\\u003c").replace(">", "\\u003e")
        head_bits.append(
            (
                '<script data-cfasync="false">window.__WOLF_WHOAMI__='
                + payload
                + ";</script>"
            ).encode("utf-8")
        )
    if head_bits:
        blob = b"".join(head_bits)
        idx = lower.find(b"</head>")
        if idx >= 0:
            out = out[:idx] + blob + out[idx:]
            lower = out.lower()
        else:
            out = blob + out
            lower = out.lower()

    # Staff Content desk uses its own header. Boards / Wolf / Up / Back / Home
    # stay on owner and system pages. Hidden UI is not a permission change.
    if not staff_ce and b'id="wolfnav"' not in lower and b"id='wolfnav'" not in lower:
        m = re.search(br"<body[^>]*>", out, re.I)
        if m:
            out = out[: m.end()] + _NAV_STUB + out[m.end() :]
            lower = out.lower()
        else:
            out = _NAV_STUB + out
            lower = out.lower()

    if not staff_ce and b"sidenav.js" not in lower:
        hook = (
            f'<script data-cfasync="false" src="/assets/sidenav.js?v={CACHE_TOKEN}"></script>'
        ).encode()
        idx = lower.find(b"</body>")
        if idx >= 0:
            out = out[:idx] + hook + out[idx:]
        else:
            out = out + hook

    return out


def refuse_proven(_: dict | None = None) -> None:
    raise WolfShellError("Do not invent PROVEN in shell UI.", code="proven_refused")


def refuse_ready(_: dict | None = None) -> None:
    raise WolfShellError("Do not invent READY in shell UI.", code="ready_refused")


def refuse_second_boards(_: dict | None = None) -> None:
    raise WolfShellError("Never a second Boards menu.", code="second_boards_refused")

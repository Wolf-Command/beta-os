/* sidenav.js — Beta Wave 1–8 + RHC V1 + Perms + Route Merge/Retire (#wolfnav).
// IA-HIDE-ORPHAN-PROVE-CRUMBS-2: Owner NeedsYou→staff-ops-routing; Exceptions→radar; BZG inventory/labor→/bzg; AMG prove crumbs off chrome
 * One chrome owner. Never a second Boards menu.
 * IA: HOME / BUSINESSES / INTELLIGENCE / SYSTEM (Target IA 2026-09-22).
 * Wave 2: Owner HOME primary = Empire; /wolf alias → Empire; Progress under SYSTEM only.
 * Wave 3: BZG crumbs WOLF › Blu Zone › Uma Blu › Today; Devi landing Uma Today.
 * Wave 4: GGV crumbs WOLF › Goss Group › GGV › …; Amanda landing GGV Overview.
 * Wave 5: AMG crumbs WOLF › Atrium Management › AMG › …; Coral landing AMG Today.
 * Wave 6: Intel crumbs WOLF › Intelligence › …; Content under Intel; Haikal → Content.
 * Wave 7: System crumbs WOLF › System › …; Progress soft-land; Sale under SYSTEM;
 *   Factory EMPTY; staff hide SYSTEM admin via nav.
 * Wave 8: mila/amanda NOT in primary IA; P0 Owner travel+learning + habitat/kuta/voice re-entry.
 * P0: Haikal Desk→/seats/content-desk, Misa Board→/seats/content-admin (roles≠person).
 *   P0: Ads Studio→/seats/ads-studio, Resolve Studio→/seats/resolve-studio (LEARN-only · no spend).
 *   P0: habitat-investment-2026, kuta-rates (AMG), amg/bzg/ggv-voice (no send).
 *   P0: trading→/owner/trading, spartacus→/owner/fitness (Owner HOME; PARTIAL).
 * RHC V1: breadcrumbs · UP / BACK / HOME · multi-assignment context switcher;
 *   P0 global shell: business switcher (IA∩clearance Owner/GGV/AMG/BZG/Uma);
 *   responsive shell prove (tokens + drawer). Visibility from whoami only —
 *   Hidden ≠ permission; API auth is canonical. No invent PROVEN/READY.
 * Perms: Person→Role→Assignment→Scope→Permission→Audience via whoami.chain;
 *   four layers CAN_SEE / CAN_ACT / CAN_SEE_DETAIL / CAN_SEE_ACROSS_SCOPE.
 * Route merge: redirect>delete server-side; primary IA unchanged (no mgmt-cluster /
 *   radar / content-brand peers / specialist / Progress-as-peer). cache-token
 *   20260922-nav-route-merge
 */
(function () {
  "use strict";

  if (window.__WOLF_SIDENAV_BOOTED__) return;
  window.__WOLF_SIDENAV_BOOTED__ = true;

  var CACHE = "20261002-owner-ux-petty";
  var EMPIRE_ALIASES = { "/owner-empire-pack": 1, "/wolf": 1 };
  var TRAIL_KEY = "wolf-shell-trail";
  /* Wave 8 — retired from primary Boards; soft-redirect handled server-side. */
  var HIDDEN_SPECIALIST_PRIMARY = {
    /* UX-PACK-03/04: Uma desk tabs + AMG/GGV hub merges.
 * UX-PACK-02: prove/deepen + voice/kuta seats off primary Boards; URLs stay live.
 * IA-HIDE-VOICE-ORPHAN-1: voice off SPECIALIST/OPERATOR audience chrome; soft-land → hubs. */
    mila: 1,
    amanda: 1,
    "ggv-voice": 1,
    "amg-voice": 1,
    "bzg-voice": 1,
    "kuta-rates": 1
  };

  var IA_TREE = [
    {
      id: "home",
      title: "HOME",
      items: [
        {
          href: "/owner-empire-pack",
          title: "Owner Home",
          key: "empire",
          primary: true,
          aliases: ["/wolf"]
        },
        {
          href: "/finish-war-room",
          title: "FINISH WOLF",
          key: "finish_wolf",
          audience: "owner"
        },
        { href: "/my-work", title: "My Work", key: "my_work" },
        { href: "/staff-ops-routing", title: "Needs You", key: "needs_you" }
        /* UX-PACK-07: Travel / Learning / Habitat Investment HIDE_UNTIL_USEFUL — routes kept */
      ]
    },
    {
      id: "personal",
      title: "PERSONAL",
      items: [
        { href: "/owner/trading", title: "Trading", key: "owner_trading", audience: "owner" },
        { href: "/owner/fitness", title: "Fitness", key: "owner_fitness", audience: "owner" },
        { href: "/owner/radar", title: "Radar", key: "owner_radar", audience: "owner" },
        { href: "/owner/travel", title: "Travel", key: "owner_travel", audience: "owner" },
        { href: "/owner/learning", title: "Learning", key: "owner_learning", audience: "owner" }
        /* UX-PACK-11: Travel/Learning unhidden as PARTIAL RO desks (Fitness pattern). Habitat Investment stays hidden. */
      ]
    },
    {
      id: "businesses",
      title: "BUSINESSES",
      /* OWNER-UX-PETTY-MOBILE-1: top = OWNER·GGV·AMG/ATRIUM·BZG; Uma under BZG outlets */
      items: [
        { href: "/ggv-ops-pack", title: "GGV", key: "ggv" },
        { href: "/amg-ops-pack", title: "AMG / Atrium", key: "amg" },
        { href: "/bzg", title: "BZG", key: "bzg" }
      ]
    },
    {
      id: "intelligence",
      title: "INTELLIGENCE",
      items: [
        { href: "/intel-ops-pack", title: "Intelligence Home", key: "intel" },
        { href: "/content-2.0", title: "Content", key: "content" }
        /* IA-TAB-INTEL-CONTENT-1: seats off primary — tabs under /content-2.0; routes kept */
      ]
    },
    {
      id: "system",
      title: "SYSTEM",
      items: [
        { href: "/progress", title: "Progress", key: "progress" },
        { href: "/integration-health", title: "Integrations", key: "integrations" },
        { href: "/sale-evidence-pack", title: "Sale Readiness", key: "sale" },
        { href: "/ops/backup-health-1", title: "Backup / DR", key: "backup" }
        /* IA-MERGE-BACKUP-SYSTEM-1: restore-drill stays HIDE */
      ]
    }
  ];

  /* Mirror of wolf_shell.ROUTE_PARENT / ROUTE_CRUMBS */
  var ROUTE_PARENT = {
    "/owner-empire-pack": null,
    "/wolf": null,
    "/staff-ops-routing": "/owner-empire-pack",
    "/finish-war-room": "/owner-empire-pack",
    "/my-work": "/owner-empire-pack",
    "/ggv-ops-pack": "/owner-empire-pack",
    "/habitat-operator": "/ggv-ops-pack",
    "/lead-spine": "/ggv-ops-pack",
    "/amg-ops-pack": "/owner-empire-pack",
    "/amg-daily-ops-state": "/amg-ops-pack",
    "/amg-journey-workflow": "/amg-ops-pack",
    "/amg-packages-products": "/amg-ops-pack",
    "/amg/occ-truth-1": "/amg-ops-pack",
    "/ggv/pipeline-truth-1": "/ggv-ops-pack",
    "/ggv-strategy-machine": "/ggv-ops-pack",
    "/ggv-social": "/ggv-ops-pack",
    "/bzg/uma-blu/evidence": "/bzg/uma-blu",
    "/bzg/uma-blu/exceptions": "/bzg/uma-blu",
    "/bzg/uma-blu/real": "/bzg/uma-blu",
    "/bzg/uma-blu/recipes": "/bzg/uma-blu",
    "/amg/finance": null,
    "/amg/finance/ledger": "/amg/finance",
    "/amg/finance/accounts": "/amg/finance",
    "/amg/finance/journals": "/amg/finance",
    "/amg/finance/reports": "/amg/finance",
    "/amg/finance/approvals": "/amg/finance",
    "/bzg": "/owner-empire-pack",
    "/bzg/uma-blu": "/bzg",
    "/bzg/uma-blu/bills": "/bzg/uma-blu",
    "/bzg/uma-blu/issues": "/bzg/uma-blu",
    "/bzg/uma-blu/petty": "/bzg/uma-blu",
    "/uma-blu-close": "/bzg/uma-blu",
    "/intel-ops-pack": "/owner-empire-pack",
    "/content-2.0": "/intel-ops-pack",
    "/progress": "/owner-empire-pack",
    "/integration-health": "/progress",
    "/sale-evidence-pack": "/progress",
    "/ops/backup-health-1": "/progress",
    "/backup-health-1": "/progress",
    "/owner/trading": "/owner-empire-pack",
    "/owner/fitness": "/owner-empire-pack",
    "/owner/travel": "/owner-empire-pack",
    "/owner/learning": "/owner-empire-pack",
    "/seats/content-desk": "/content-2.0",
    "/seats/content-admin": "/content-2.0",
    "/seats/ads-studio": "/content-2.0",
    "/seats/resolve-studio": "/content-2.0",
    "/habitat-investment-2026": "/owner-empire-pack",
    "/kuta-rates": "/amg-ops-pack",
    "/amg-voice": "/amg-ops-pack",
    "/bzg-voice": "/bzg",
    "/ggv-voice": "/ggv-ops-pack"
  };

  var ROUTE_CRUMBS = {
    "/owner-empire-pack": [
      { label: "HOME", href: "/wolf" },
      { label: "Owner Home", href: null }
    ],
    "/wolf": [
      { label: "HOME", href: "/wolf" },
      { label: "Owner Home", href: null }
    ],
    "/finish-war-room": [
      { label: "HOME", href: "/wolf" },
      { label: "FINISH WOLF", href: null }
    ],
    "/my-work": [
      { label: "HOME", href: "/wolf" },
      { label: "My Work", href: null }
    ],
    "/staff-ops-routing": [
      { label: "HOME", href: "/wolf" },
      { label: "Needs You", href: null }
    ],
    "/owner/trading": [
      { label: "HOME", href: "/wolf" },
      { label: "Personal", href: "/owner-empire-pack" },
      { label: "Trading", href: null }
    ],
    "/owner/fitness": [
      { label: "HOME", href: "/wolf" },
      { label: "Personal", href: "/owner-empire-pack" },
      { label: "Fitness", href: null }
    ],
    "/owner/radar": [
      { label: "HOME", href: "/wolf" },
      { label: "Personal", href: "/owner-empire-pack" },
      { label: "Radar", href: null }
    ],
    "/owner/travel": [
      { label: "HOME", href: "/wolf" },
      { label: "Personal", href: "/owner-empire-pack" },
      { label: "Travel", href: null }
    ],
    "/owner/learning": [
      { label: "HOME", href: "/wolf" },
      { label: "Personal", href: "/owner-empire-pack" },
      { label: "Learning", href: null }
    ],
    "/ggv-ops-pack": [
      { label: "WOLF", href: "/wolf" },
      { label: "Goss Group", href: null },
      { label: "GGV", href: null }
    ],
    "/habitat-operator": [
      { label: "WOLF", href: "/wolf" },
      { label: "Goss Group", href: null },
      { label: "GGV", href: "/ggv-ops-pack" },
      { label: "Habitat", href: null }
    ],
    "/lead-spine": [
      { label: "WOLF", href: "/wolf" },
      { label: "Goss Group", href: null },
      { label: "GGV", href: "/ggv-ops-pack" },
      { label: "Lead Spine", href: null }
    ],
    "/amg-ops-pack": [
      { label: "WOLF", href: "/wolf" },
      { label: "Atrium Management", href: null },
      { label: "AMG", href: null }
    ],
    "/amg-daily-ops-state": [
      { label: "WOLF", href: "/wolf" },
      { label: "Atrium Management", href: null },
      { label: "AMG", href: "/amg-ops-pack" },
      { label: "Daily Ops", href: null }
    ],

    "/amg-journey-workflow": [
      { label: "WOLF", href: "/wolf" },
      { label: "Atrium Management", href: "/amg-ops-pack" },
      { label: "AMG", href: "/amg-ops-pack" },
      { label: "Journey", href: null }
    ],
    "/amg-packages-products": [
      { label: "WOLF", href: "/wolf" },
      { label: "Atrium Management", href: "/amg-ops-pack" },
      { label: "AMG", href: "/amg-ops-pack" },
      { label: "Packages", href: null }
    ],
    "/amg/occ-truth-1": [
      { label: "WOLF", href: "/wolf" },
      { label: "Atrium Management", href: "/amg-ops-pack" },
      { label: "AMG", href: "/amg-ops-pack" },
      { label: "OCC", href: null }
    ],
    "/ggv/pipeline-truth-1": [
      { label: "WOLF", href: "/wolf" },
      { label: "Goss Group", href: "/ggv-ops-pack" },
      { label: "GGV", href: "/ggv-ops-pack" },
      { label: "Pipeline", href: null }
    ],
    "/ggv-strategy-machine": [
      { label: "WOLF", href: "/wolf" },
      { label: "Goss Group", href: "/ggv-ops-pack" },
      { label: "GGV", href: "/ggv-ops-pack" },
      { label: "Strategy", href: null }
    ],
    "/ggv-social": [
      { label: "WOLF", href: "/wolf" },
      { label: "Goss Group", href: "/ggv-ops-pack" },
      { label: "GGV", href: "/ggv-ops-pack" },
      { label: "Social", href: null }
    ],
    "/bzg/uma-blu/evidence": [
      { label: "WOLF", href: "/wolf" },
      { label: "Blu Zone", href: "/bzg" },
      { label: "Uma Blu", href: "/bzg/uma-blu" },
      { label: "Evidence", href: null }
    ],
    "/bzg/uma-blu/exceptions": [
      { label: "WOLF", href: "/wolf" },
      { label: "Blu Zone", href: "/bzg" },
      { label: "Uma Blu", href: "/bzg/uma-blu" },
      { label: "Exceptions", href: null }
    ],
    "/bzg/uma-blu/real": [
      { label: "WOLF", href: "/wolf" },
      { label: "Blu Zone", href: "/bzg" },
      { label: "Uma Blu", href: "/bzg/uma-blu" },
      { label: "Real", href: null }
    ],
    "/bzg/uma-blu/recipes": [
      { label: "WOLF", href: "/wolf" },
      { label: "Blu Zone", href: "/bzg" },
      { label: "Uma Blu", href: "/bzg/uma-blu" },
      { label: "Recipes", href: null }
    ],
    "/amg/finance": [
      { label: "Atrium Finance", href: null }
    ],
    "/amg/finance/ledger": [
      { label: "Atrium Finance", href: "/amg/finance" },
      { label: "Ledger", href: null }
    ],
    "/amg/finance/accounts": [
      { label: "Atrium Finance", href: "/amg/finance" },
      { label: "Chart of Accounts", href: null }
    ],
    "/amg/finance/journals": [
      { label: "Atrium Finance", href: "/amg/finance" },
      { label: "Journals", href: null }
    ],
    "/amg/finance/reports": [
      { label: "Atrium Finance", href: "/amg/finance" },
      { label: "Reports", href: null }
    ],
    "/amg/finance/approvals": [
      { label: "Atrium Finance", href: "/amg/finance" },
      { label: "Approvals", href: null }
    ],
    "/bzg": [
      { label: "WOLF", href: "/wolf" },
      { label: "Blu Zone", href: null }
    ],
    "/bzg/uma-blu": [
      { label: "WOLF", href: "/wolf" },
      { label: "Blu Zone", href: "/bzg" },
      { label: "Uma Blu", href: "/bzg/uma-blu" },
      { label: "Today", href: null }
    ],
    "/bzg/uma-blu/bills": [
      { label: "WOLF", href: "/wolf" },
      { label: "Blu Zone", href: "/bzg" },
      { label: "Uma Blu", href: "/bzg/uma-blu" },
      { label: "Bills", href: null }
    ],
    "/bzg/uma-blu/issues": [
      { label: "WOLF", href: "/wolf" },
      { label: "Blu Zone", href: "/bzg" },
      { label: "Uma Blu", href: "/bzg/uma-blu" },
      { label: "Issues", href: null }
    ],
    "/bzg/uma-blu/petty": [
      { label: "WOLF", href: "/wolf" },
      { label: "Blu Zone", href: "/bzg" },
      { label: "Uma Blu", href: "/bzg/uma-blu" },
      { label: "Petty", href: null }
    ],
    "/uma-blu-close": [
      { label: "WOLF", href: "/wolf" },
      { label: "Blu Zone", href: "/bzg" },
      { label: "Uma Blu", href: "/bzg/uma-blu" },
      { label: "Close", href: null }
    ],
    "/intel-ops-pack": [
      { label: "WOLF", href: "/wolf" },
      { label: "Intelligence", href: null }
    ],
    "/content-2.0": [
      { label: "WOLF", href: "/wolf" },
      { label: "Intelligence", href: "/intel-ops-pack" },
      { label: "Content", href: null }
    ],
    "/seats/content-desk": [
      { label: "WOLF", href: "/wolf" },
      { label: "Intelligence", href: "/intel-ops-pack" },
      { label: "Content", href: "/content-2.0" },
      { label: "Content Desk (seat)", href: null }
    ],
    "/seats/content-admin": [
      { label: "WOLF", href: "/wolf" },
      { label: "Intelligence", href: "/intel-ops-pack" },
      { label: "Content", href: "/content-2.0" },
      { label: "Content Admin (seat)", href: null }
    ],
    "/seats/ads-studio": [
      { label: "WOLF", href: "/wolf" },
      { label: "Intelligence", href: "/intel-ops-pack" },
      { label: "Content", href: "/content-2.0" },
      { label: "Ads Studio (seat)", href: null }
    ],
    "/seats/resolve-studio": [
      { label: "WOLF", href: "/wolf" },
      { label: "Intelligence", href: "/intel-ops-pack" },
      { label: "Content", href: "/content-2.0" },
      { label: "Resolve Studio (seat)", href: null }
    ],
    "/habitat-investment-2026": [
      { label: "HOME", href: "/wolf" },
      { label: "Habitat Investment (Owner)", href: null }
    ],
    "/kuta-rates": [
      { label: "WOLF", href: "/wolf" },
      { label: "Atrium Management", href: null },
      { label: "AMG", href: "/amg-ops-pack" },
      { label: "Kuta Rates", href: null }
    ],
    "/amg-voice": [
      { label: "WOLF", href: "/wolf" },
      { label: "Atrium Management", href: null },
      { label: "AMG", href: "/amg-ops-pack" },
      { label: "Voice (seat)", href: null }
    ],
    "/bzg-voice": [
      { label: "WOLF", href: "/wolf" },
      { label: "Blu Zone", href: "/bzg" },
      { label: "Voice (seat)", href: null }
    ],
    "/ggv-voice": [
      { label: "WOLF", href: "/wolf" },
      { label: "Goss Group", href: null },
      { label: "GGV", href: "/ggv-ops-pack" },
      { label: "Voice (seat)", href: null }
    ],
    "/progress": [
      { label: "WOLF", href: "/wolf" },
      { label: "System", href: null },
      { label: "Progress", href: null }
    ],
    "/integration-health": [
      { label: "WOLF", href: "/wolf" },
      { label: "System", href: "/progress" },
      { label: "Integrations", href: null }
    ],
    "/sale-evidence-pack": [
      { label: "WOLF", href: "/wolf" },
      { label: "System", href: "/progress" },
      { label: "Sale", href: null }
    ]
  };

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function phone() {
    var ua = navigator.userAgent || "";
    if (/iPhone|iPod/i.test(ua)) return true;
    if (/Android/i.test(ua) && /Mobile/i.test(ua)) return true;
    var sw = (window.screen && screen.width) || 0;
    if (sw > 0 && sw <= 430) return true;
    var w = window.innerWidth || 0;
    try {
      if (window.matchMedia("(max-width: 860px)").matches) return true;
    } catch (e) {}
    return w > 0 && w < 860;
  }

  function applyMode() {
    var on = phone();
    document.documentElement.classList.toggle("wolfnav-phone", on);
    document.documentElement.classList.toggle("wolfnav-desktop", !on);
    document.documentElement.classList.toggle("wolf-switch-narrow", on);
    placeBoardsPanel();
  }

  function syncNavHeight() {
    var nav = document.getElementById("wolfnav");
    if (!nav) return;
    var h = Math.round(nav.getBoundingClientRect().height || 56);
    document.documentElement.style.setProperty("--wolf-nav-h", Math.max(44, h) + "px");
  }

  function setBoardsOpen(on) {
    var nav = document.getElementById("wolfnav");
    if (!nav) return;
    syncNavHeight();
    placeBoardsPanel();
    nav.classList.toggle("boards-open", !!on);
    document.body.classList.toggle("wolf-boards-open", !!on);
    var btn = document.getElementById("wolfnav-t");
    if (btn) btn.setAttribute("aria-expanded", on ? "true" : "false");
  }

  function placeBoardsPanel(panel) {
    var nav = document.getElementById("wolfnav");
    panel = panel || document.getElementById("wolf-boards");
    if (!nav || !panel || !document.body) return;
    if (phone()) {
      if (panel.parentNode !== document.body) document.body.appendChild(panel);
    } else if (panel.parentNode !== nav) {
      nav.appendChild(panel);
    }
  }

  function whoami() {
    return (typeof window !== "undefined" && window.__WOLF_WHOAMI__) || null;
  }

  function normPath(p) {
    var s = String(p || "").split("?")[0].split("#")[0];
    if (!s) return "/";
    if (s.charAt(0) !== "/") s = "/" + s;
    if (s.length > 1 && s.slice(-1) === "/") s = s.slice(0, -1);
    return s.toLowerCase();
  }

  function sameDest(a, b) {
    var pa = normPath(a);
    var pb = normPath(b);
    if (pa === pb) return true;
    if (EMPIRE_ALIASES[pa] && EMPIRE_ALIASES[pb]) return true;
    return false;
  }

  function itemMatchesHere(it, here) {
    if (sameDest(it.href, here)) return true;
    var aliases = it.aliases || [];
    var i;
    for (i = 0; i < aliases.length; i++) {
      if (sameDest(aliases[i], here)) return true;
    }
    return false;
  }

  function pageAllowed(href, who) {
    who = who || whoami();
    if (!who) return false;
    if (who.wolf_authorized === true || who.audience === "OWNER") return true;
    if (who.scoped === false && who.pages == null) return true;
    var pages = who.pages;
    if (!Array.isArray(pages)) return false;
    var target = normPath(href);
    if (EMPIRE_ALIASES[target]) {
      var e;
      for (e = 0; e < pages.length; e++) {
        if (EMPIRE_ALIASES[normPath(pages[e])]) return true;
      }
    }
    var i;
    for (i = 0; i < pages.length; i++) {
      if (normPath(pages[i]) === target) return true;
    }
    return false;
  }

  function filterTree(who) {
    var out = [];
    IA_TREE.forEach(function (sec) {
      var kids = [];
      (sec.items || []).forEach(function (it) {
        if (pageAllowed(it.href, who)) kids.push(it);
      });
      if (kids.length) out.push({ id: sec.id, title: sec.title, items: kids });
    });
    return out;
  }

  function herePath() {
    return normPath(location.pathname || "/");
  }

  function homeHref(who) {
    who = who || whoami();
    if (!who) return null;
    return who.landing || who.home_primary || null;
  }

  function parentHref(path, who) {
    var p = normPath(path);
    var parent = Object.prototype.hasOwnProperty.call(ROUTE_PARENT, p)
      ? ROUTE_PARENT[p]
      : undefined;
    if (parent === null) return null;
    if (parent === undefined && EMPIRE_ALIASES[p]) return null;
    if (parent && pageAllowed(parent, who)) return parent;
    return homeHref(who);
  }

  function readTrail() {
    try {
      var raw = sessionStorage.getItem(TRAIL_KEY);
      var arr = raw ? JSON.parse(raw) : [];
      return Array.isArray(arr) ? arr : [];
    } catch (e) {
      return [];
    }
  }

  function writeTrail(arr) {
    try {
      sessionStorage.setItem(TRAIL_KEY, JSON.stringify(arr.slice(-24)));
    } catch (e) {}
  }

  function rememberHere() {
    var here = herePath();
    var trail = readTrail();
    if (!trail.length || trail[trail.length - 1] !== here) {
      trail.push(here);
      writeTrail(trail);
    }
  }

  function backHref(who) {
    var here = herePath();
    var trail = readTrail();
    var i;
    for (i = trail.length - 2; i >= 0; i--) {
      if (trail[i] !== here && pageAllowed(trail[i], who)) return trail[i];
    }
    return parentHref(here, who) || homeHref(who);
  }

  function crumbsFor(path, who) {
    var p = normPath(path);
    var trail = ROUTE_CRUMBS[p];
    if (!trail && EMPIRE_ALIASES[p]) trail = ROUTE_CRUMBS["/wolf"];
    if (!trail) return [{ label: "Here", href: null }];
    var landing = homeHref(who);
    return trail.map(function (c) {
      var out = { label: c.label, href: c.href };
      if (out.href && !pageAllowed(out.href, who)) {
        if ((out.label === "HOME" || out.label === "WOLF") && landing) out.href = landing;
        else out.href = null;
      }
      return out;
    });
  }

  function renderBoards(panel, who) {
    var tree = filterTree(who);
    var here = herePath();
    var html = [];
    if (!tree.length) {
      html.push('<div class="wolf-switch-h">No destinations</div>');
      html.push(
        '<p class="nv-ask-hint" style="padding:8px 12px;color:var(--muted,#8aa6a6);font-size:12px;font-weight:500">Hidden menu is not permission. Ask an admin if you need access.</p>'
      );
    } else {
      tree.forEach(function (sec) {
        html.push('<details class="nv-group" open>');
        html.push("<summary>" + esc(sec.title) + "</summary>");
        (sec.items || []).forEach(function (it) {
          var cls = itemMatchesHere(it, here) ? " here" : "";
          if (it.primary) cls += " primary";
          html.push(
            '<a class="nv-child' +
              cls +
              '" href="' +
              esc(it.href) +
              '">' +
              esc(it.title) +
              "</a>"
          );
        });
        html.push("</details>");
      });
    }
    panel.innerHTML = html.join("");
  }

  function paintCrumbs(el, who) {
    if (!el) return;
    var crumbs = crumbsFor(herePath(), who);
    var narrow = phone();
    var html = [];
    var i;
    if (narrow && crumbs.length > 2) {
      var parent = crumbs[crumbs.length - 2];
      var cur = crumbs[crumbs.length - 1];
      if (parent.href) {
        html.push(
          '<a class="nv-crumb" href="' + esc(parent.href) + '">' + esc(parent.label) + "</a>"
        );
      } else {
        html.push('<span class="nv-crumb">' + esc(parent.label) + "</span>");
      }
      html.push('<span class="nv-crumb-sep" aria-hidden="true">›</span>');
      html.push('<span class="nv-crumb here">' + esc(cur.label) + "</span>");
      el.setAttribute(
        "title",
        crumbs
          .map(function (c) {
            return c.label;
          })
          .join(" › ")
      );
    } else {
      for (i = 0; i < crumbs.length; i++) {
        if (i) html.push('<span class="nv-crumb-sep" aria-hidden="true">›</span>');
        var c = crumbs[i];
        if (c.href && i < crumbs.length - 1) {
          html.push(
            '<a class="nv-crumb" href="' + esc(c.href) + '">' + esc(c.label) + "</a>"
          );
        } else {
          html.push(
            '<span class="nv-crumb' +
              (i === crumbs.length - 1 ? " here" : "") +
              '">' +
              esc(c.label) +
              "</span>"
          );
        }
      }
      el.removeAttribute("title");
    }
    el.innerHTML = html.join("");
  }

  function paintDir(who) {
    var up = document.getElementById("wolfnav-up");
    var back = document.getElementById("wolfnav-back");
    var home = document.getElementById("wolfnav-home");
    var here = herePath();
    var upH = parentHref(here, who);
    var backH = backHref(who);
    var homeH = homeHref(who);

    function wire(el, href, label) {
      if (!el) return;
      if (href) {
        el.href = href;
        el.removeAttribute("aria-disabled");
        el.classList.remove("is-disabled");
        el.title = label;
      } else {
        el.href = "#";
        el.setAttribute("aria-disabled", "true");
        el.classList.add("is-disabled");
        el.title = label + " unavailable";
        el.onclick = function (e) {
          if (e) e.preventDefault();
          return false;
        };
      }
    }

    wire(up, upH, "Up to parent");
    wire(back, backH, "Back to prior context");
    wire(home, homeH, "Authorised home");
    if (up && upH) {
      up.onclick = null;
    }
    if (back && backH) {
      back.onclick = null;
    }
    if (home && homeH) {
      home.onclick = null;
    }
  }

  
  function businessCatalogFallback() {
    /* Mirror IA_TREE derivation when whoami.businesses absent (stale bake). */
    var out = [];
    var i, j, sec, it;
    for (i = 0; i < IA_TREE.length; i++) {
      sec = IA_TREE[i];
      if (sec.id === "home") {
        for (j = 0; j < sec.items.length; j++) {
          it = sec.items[j];
          if (it.key === "empire") {
            out.push({
              id: "owner",
              key: "owner",
              title: "Owner",
              href: "/wolf",
              aliases: (it.aliases || []).concat(["/owner-empire-pack"])
            });
          }
        }
      }
      if (sec.id === "businesses") {
        for (j = 0; j < sec.items.length; j++) {
          it = sec.items[j];
          var short =
            it.key === "ggv"
              ? "GGV"
              : it.key === "amg"
                ? "AMG"
                : it.key === "bzg"
                  ? "BZG"
                  : it.key === "uma"
                    ? "Uma Blu"
                    : it.title;
          out.push({
            id: it.key,
            key: it.key,
            title: short,
            href: it.href,
            aliases: it.aliases || []
          });
        }
      }
    }
    return out;
  }

  function navBizSource(who) {
    /* Prefer Assignment/Role/Scope authority; honesty stamp when transitional. */
    who = who || whoami();
    try {
      var auth = who && who.nav_authority;
      if (auth && auth.ok !== false) {
        var ab = auth.businesses;
        if (Array.isArray(ab) && ab.length) return "authority";
      }
    } catch (e) {
      /* authority missing/error → transitional fallback */
    }
    return "ia_intersect_pages_transitional";
  }

  function businessesFor(who) {
    who = who || whoami();
    /* Prefer nav_authority.businesses (ROLE+SCOPE). Safe fallback to IA∩pages. */
    try {
      var auth = who && who.nav_authority;
      if (auth && auth.ok !== false) {
        var authBiz = auth.businesses;
        if (Array.isArray(authBiz) && authBiz.length) return authBiz;
      }
    } catch (e) {
      /* fall through */
    }
    var baked = (who && who.businesses) || [];
    if (baked && baked.length) return baked;
    var cat = businessCatalogFallback();
    var out = [];
    var i;
    for (i = 0; i < cat.length; i++) {
      if (pageAllowed(cat[i].href, who)) out.push(cat[i]);
      else {
        var als = cat[i].aliases || [];
        var ok = false;
        var a;
        for (a = 0; a < als.length; a++) {
          if (pageAllowed(als[a], who)) {
            ok = true;
            break;
          }
        }
        if (ok) out.push(cat[i]);
      }
    }
    return out;
  }

  function activeBusinessId(biz, who) {
    who = who || whoami();
    /* Path wins so BZG/Uma routes highlight BZG (not sticky Owner landing). */
    var path = (location.pathname || "/").replace(/\/+$/, "") || "/";
    var best = null;
    var bestLen = -1;
    var b, cands, c, h, hr;
    var bids = {};
    for (b = 0; b < biz.length; b++) bids[biz[b].id] = 1;
    for (b = 0; b < biz.length; b++) {
      cands = [biz[b].href].concat(biz[b].aliases || []);
      if (biz[b].id === "bzg" && !bids.uma) {
        cands = cands.concat(["/bzg/uma-blu", "/bzg/uma-blu/"]);
      }
      for (c = 0; c < cands.length; c++) {
        h = cands[c];
        if (!h) continue;
        hr = String(h).replace(/\/+$/, "") || "/";
        if (
          path === hr ||
          path.indexOf(hr + "/") === 0 ||
          (EMPIRE_ALIASES[hr] && (EMPIRE_ALIASES[path] || path.indexOf("/owner/") === 0))
        ) {
          if (hr.length > bestLen) {
            bestLen = hr.length;
            best = biz[b].id;
          }
        }
      }
    }
    if (best) return best;
    if (who && who.active_business_id) {
      for (b = 0; b < biz.length; b++) {
        if (biz[b].id === who.active_business_id) return who.active_business_id;
      }
    }
    return best;
  }

  function activeOutletId(outlets, who) {
    who = who || whoami();
    var path = (location.pathname || "/").replace(/\/+$/, "") || "/";
    var best = null;
    var bestLen = -1;
    var o, cands, c, h, hr;
    for (o = 0; o < outlets.length; o++) {
      cands = [outlets[o].href].concat(outlets[o].aliases || []);
      for (c = 0; c < cands.length; c++) {
        h = cands[c];
        if (!h || h === "/bzg/outlets" || h === "/bzg/outlets/") continue;
        hr = String(h).replace(/\/+$/, "") || "/";
        if (path === hr || path.indexOf(hr + "/") === 0) {
          if (hr.length > bestLen) {
            bestLen = hr.length;
            best = outlets[o].id;
          }
        }
      }
    }
    if (best) return best;
    return (who && who.active_outlet_id) || null;
  }

  function paintBusiness(el, who) {
    if (!el) return;
    who = who || whoami();
    var source = navBizSource(who);
    var biz = businessesFor(who);
    var show = biz.length >= 1;
    if (!show) {
      el.hidden = true;
      el.innerHTML = "";
      el.removeAttribute("data-wolf-biz");
      el.removeAttribute("data-nav-source");
      el.removeAttribute("data-wolf-nav-honesty");
      return;
    }
    el.hidden = false;
    el.setAttribute("data-wolf-biz", biz.length > 1 ? "multi" : "single");
    el.setAttribute("data-nav-source", source);
    el.setAttribute(
      "data-wolf-nav-honesty",
      source === "authority" ? "authority_chrome" : "ia_intersect_pages_transitional"
    );
    var active = activeBusinessId(biz, who);
    var chips = biz
      .map(function (b) {
        if (!pageAllowed(b.href, who) && !(b.aliases || []).some(function (a) {
          return pageAllowed(a, who);
        })) {
          return "";
        }
        var isOn = b.id === active;
        return (
          '<a class="nv-biz-chip' +
          (isOn ? " is-active" : "") +
          '" href="' +
          esc(b.href) +
          '" data-biz-id="' +
          esc(b.id) +
          '" data-nav-source="' +
          esc(source) +
          '" aria-current="' +
          (isOn ? "page" : "false") +
          '">' +
          esc(b.title) +
          "</a>"
        );
      })
      .join("");
    var outlets = (who && who.outlet_children) || [];
    var path = (location.pathname || "/").replace(/\/+$/, "") || "/";
    var showOutlets =
      outlets.length > 0 &&
      (active === "bzg" || active === "uma" || path.indexOf("/bzg") === 0);
    var activeOut = showOutlets ? activeOutletId(outlets, who) : null;
    var outletChips = "";
    if (showOutlets) {
      outletChips =
        '<div class="nv-outlet-chips" role="navigation" aria-label="BZG outlets">' +
        outlets
          .map(function (o) {
            var label = o.chip_label || o.title || o.id;
            var isOn = o.id === activeOut;
            var pre = o.status === "PRE-OPENING" ? ' data-outlet-status="PRE-OPENING"' : "";
            return (
              '<a class="nv-outlet-chip' +
              (isOn ? " is-active" : "") +
              '" href="' +
              esc(o.href) +
              '" data-outlet-id="' +
              esc(o.id) +
              '"' +
              pre +
              ' aria-current="' +
              (isOn ? "page" : "false") +
              '">' +
              esc(label) +
              "</a>"
            );
          })
          .join("") +
        "</div>";
    }
    el.innerHTML =
      '<span class="nv-biz-label" id="wolfnav-biz-label">Business</span>' +
      '<div class="nv-biz-chips" role="navigation" aria-labelledby="wolfnav-biz-label">' +
      chips +
      "</div>" +
      outletChips;
    var links = el.querySelectorAll("a.nv-biz-chip, a.nv-outlet-chip");
    var i;
    for (i = 0; i < links.length; i++) {
      links[i].onclick = function (e) {
        var href = this.getAttribute("href");
        if (!href || (!pageAllowed(href, who) && href.indexOf("/bzg") !== 0)) {
          if (e) e.preventDefault();
          return false;
        }
        return true;
      };
    }
  }

  var SCOPE_BUSINESS_LABEL = {
    "SCOPE-AMG-FINANCE": "Atrium",
    "SCOPE-AMG": "Atrium",
    "SCOPE-AMG-ATR-DAY": "Atrium",
    "SCOPE-BZG-FINANCE": "Blu Zone Group",
    "SCOPE-BZG-ENTITY": "Blu Zone Group",
    "SCOPE-BZG-FB": "Blu Zone Group",
    "SCOPE-BZG-UMA": "Uma Blu",
    "SCOPE-GGV-FINANCE": "GGV",
    "SCOPE-GGV-ALL": "GGV",
    "SCOPE-GGV": "GGV",
    "SCOPE-GGV-CONTENT": "GGV",
    "SCOPE-GGV-HABITAT-LEAD": "GGV",
    "SCOPE-WOLF-GROUP": "Wolf Group",
    "SCOPE-CORE-OPERATOR": "Core",
    "SCOPE-SALE-OPERATOR": "Sale",
  };

  function seatOptionLabel(a) {
    var label = String((a && a.label) || "").trim();
    var scope = String((a && a.scope) || "").trim();
    var biz = SCOPE_BUSINESS_LABEL[scope] || "";
    if (label && biz) return label + " — " + biz;
    return label || biz || "Seat";
  }

function paintContext(el, who) {
    if (!el) return;
    var asg = (who && who.assignments) || [];
    var show = who && who.context_switcher === true && asg.length > 1;
    if (!show) {
      el.hidden = true;
      el.innerHTML = "";
      el.removeAttribute("data-wolf-ctx");
      return;
    }
    el.hidden = false;
    el.setAttribute("data-wolf-ctx", "multi");
    var active = (who && who.active_assignment_id) || (asg[0] && asg[0].id);
    var opts = asg
      .map(function (a) {
        if (!pageAllowed(a.href, who)) return "";
        var sel = a.id === active ? " selected" : "";
        return (
          '<option value="' +
          esc(a.id) +
          '" data-href="' +
          esc(a.href) +
          '"' +
          sel +
          ">" +
          esc(seatOptionLabel(a)) +
          "</option>"
        );
      })
      .join("");
    /* Advanced only — human-labeled; Owner chrome hides this (server context_switcher=false). */
    el.innerHTML =
      '<label class="nv-ctx-label" for="wolfnav-ctx-select">Seat</label>' +
      '<select id="wolfnav-ctx-select" class="nv-ctx-select" aria-label="Switch authorised seat">' +
      opts +
      "</select>";
    var sel = document.getElementById("wolfnav-ctx-select");
    if (sel) {
      sel.onchange = function () {
        var opt = sel.options[sel.selectedIndex];
        var href = opt && opt.getAttribute("data-href");
        if (href && pageAllowed(href, who)) {
          location.href = href;
        }
      };
    }
  }

  function ensureChrome() {
    var nav = document.getElementById("wolfnav");
    if (!nav) {
      nav = document.createElement("nav");
      nav.id = "wolfnav";
      nav.setAttribute("aria-label", "Wolf global navigation");
      if (document.body.firstChild) {
        document.body.insertBefore(nav, document.body.firstChild);
      } else {
        document.body.appendChild(nav);
      }
    }
    /* Never create a second #wolfnav */
    var extras = document.querySelectorAll("#wolfnav");
    if (extras.length > 1) {
      for (var i = 1; i < extras.length; i++) extras[i].parentNode.removeChild(extras[i]);
    }

    var row = nav.querySelector(".nv-row");
    if (!row) {
      row = document.createElement("div");
      row.className = "nv-row";
      nav.appendChild(row);
    }

    var btn = document.getElementById("wolfnav-t");
    if (!btn) {
      btn = document.createElement("button");
      btn.type = "button";
      btn.id = "wolfnav-t";
      btn.setAttribute("aria-label", "Boards");
      btn.setAttribute("aria-expanded", "false");
      btn.setAttribute("aria-controls", "wolf-boards");
      btn.textContent = "Boards";
      row.insertBefore(btn, row.firstChild);
    }

    var brand = document.getElementById("wolfnav-brand");
    if (!brand) {
      brand = document.createElement("div");
      brand.className = "nv-brand";
      brand.id = "wolfnav-brand";
      brand.innerHTML = "<b>Wolf</b>";
      if (btn.nextSibling) row.insertBefore(brand, btn.nextSibling);
      else row.appendChild(brand);
    }

    var dir = document.getElementById("wolfnav-dir");
    if (!dir) {
      dir = document.createElement("div");
      dir.className = "nv-dir";
      dir.id = "wolfnav-dir";
      dir.setAttribute("role", "group");
      dir.setAttribute("aria-label", "Direction");
      dir.innerHTML =
        '<a class="nv-dir-btn" id="wolfnav-up" href="#" data-wolf-dir="up">Up</a>' +
        '<a class="nv-dir-btn" id="wolfnav-back" href="#" data-wolf-dir="back">Back</a>' +
        '<a class="nv-dir-btn" id="wolfnav-home" href="#" data-wolf-dir="home">Home</a>';
      row.insertBefore(dir, brand.nextSibling);
    }

    var crumbs = document.getElementById("wolfnav-crumbs");
    if (!crumbs) {
      crumbs = document.createElement("nav");
      crumbs.className = "nv-crumbs";
      crumbs.id = "wolfnav-crumbs";
      crumbs.setAttribute("aria-label", "Breadcrumb");
      row.insertBefore(crumbs, dir.nextSibling);
    }

    var biz = document.getElementById("wolfnav-biz");
    if (!biz) {
      biz = document.createElement("div");
      biz.className = "nv-biz";
      biz.id = "wolfnav-biz";
      biz.hidden = true;
      row.insertBefore(biz, crumbs.nextSibling);
    }

    var ctx = document.getElementById("wolfnav-ctx");
    if (!ctx) {
      ctx = document.createElement("div");
      ctx.className = "nv-ctx";
      ctx.id = "wolfnav-ctx";
      ctx.hidden = true;
      row.insertBefore(ctx, biz.nextSibling);
    }

    var hello = document.getElementById("wolfnav-hello");
    if (!hello) {
      hello = document.createElement("div");
      hello.className = "nv-hello";
      hello.id = "wolfnav-hello";
      row.appendChild(hello);
    }

    var footer = nav.querySelector(".nv-footer");
    if (!footer) {
      footer = document.createElement("div");
      footer.className = "nv-footer";
      var signout = document.createElement("a");
      signout.href = "/signout";
      signout.textContent = "Sign out";
      signout.title = "End session";
      footer.appendChild(signout);
      row.appendChild(footer);
    }

    var panel = document.getElementById("wolf-boards");
    if (!panel) {
      panel = document.createElement("div");
      panel.id = "wolf-boards";
      panel.setAttribute("role", "menu");
      nav.appendChild(panel);
    }

    var scrim = document.getElementById("wolfnav-scrim");
    if (!scrim) {
      scrim = document.createElement("div");
      scrim.id = "wolfnav-scrim";
      document.body.appendChild(scrim);
    }

    btn.onclick = function (e) {
      if (e) {
        e.preventDefault();
        e.stopPropagation();
      }
      setBoardsOpen(!nav.classList.contains("boards-open"));
      return false;
    };
    scrim.onclick = function () {
      setBoardsOpen(false);
    };

    document.body.classList.add("wolfnav-on", "wolfnav-open");
    document.body.classList.remove("wolfnav-closed");
    return {
      nav: nav,
      panel: panel,
      hello: hello,
      crumbs: crumbs,
      biz: document.getElementById("wolfnav-biz"),
      ctx: ctx
    };
  }

  function roleTitleForStaff(who) {
    /* Plain seat title only — never ROLE-* / SPECIALIST_* codes for staff. */
    var asg = (who && who.assignments) || [];
    var path = (location && location.pathname) || "";
    var i;
    for (i = 0; i < asg.length; i += 1) {
      var href = String((asg[i] && asg[i].href) || "");
      if (!href) continue;
      if (path === href || path.indexOf(href + "/") === 0) {
        return String((asg[i] && asg[i].label) || "");
      }
    }
    var active = who && who.active_assignment;
    if (active && active.label) return String(active.label);
    if (asg.length && asg[0] && asg[0].label) return String(asg[0].label);
    var rl = (who && who.role_label) || "";
    if (rl && rl.indexOf("SPECIALIST_") !== 0 && rl.indexOf("ROLE-") !== 0) {
      return String(rl);
    }
    return "";
  }

  function roleForActiveContext(who) {
    /* Prefer ROLE-* codes for owner/debug chrome. Staff paintHello uses roleTitleForStaff. */
    var asg = (who && who.assignments) || [];
    var path = (location && location.pathname) || "";
    var i;
    for (i = 0; i < asg.length; i += 1) {
      var href = String((asg[i] && asg[i].href) || "");
      if (!href) continue;
      if (path === href || path.indexOf(href + "/") === 0) {
        return String(asg[i].role || asg[i].label || "");
      }
    }
    var active = who && who.active_assignment;
    if (active && (active.role || active.label)) {
      return String(active.role || active.label);
    }
    var roles = (who && who.roles) || ((who && who.chain) || {}).roles || [];
    return roles.length ? String(roles[0]) : "";
  }

  function paintHello(hello, who) {
    if (!hello) return;
    var chain = (who && who.chain) || {};
    var aud = (who && who.audience) || chain.audience || "";
    var isOwner =
      who &&
      (who.wolf_authorized === true || aud === "OWNER" || aud === "SYSTEM");
    var name =
      (who && (who.hello || who.given_name || who.email)) || "";
    if (isOwner) {
      /* OWNER-UX-PETTY-MOBILE-1: plain human hello — no ROLE-* / audience dump on chrome. */
      var ownerLabel = name || "Owner";
      hello.textContent = String(ownerLabel);
      return;
    }
    /* Staff: plain role title only (optional name · title). Never SPECIALIST_/ROLE- codes. */
    var roleTitle = roleTitleForStaff(who);
    if (name && roleTitle) hello.textContent = name + " · " + roleTitle;
    else if (roleTitle) hello.textContent = roleTitle;
    else if (name) hello.textContent = String(name);
    else hello.textContent = "";
  }

  function bootWith(who) {
    applyMode();
    var parts = ensureChrome();
    paintHello(parts.hello, who);
    renderBoards(parts.panel, who);
    rememberHere();
    paintCrumbs(parts.crumbs, who);
    paintDir(who);
    paintBusiness(parts.biz, who);
    paintContext(parts.ctx, who);
    syncNavHeight();
    if (phone()) setBoardsOpen(false);
  }

  function fetchWhoami(cb) {
    var baked = whoami();
    if (baked && (baked.pages || baked.wolf_authorized != null || baked.audience)) {
      cb(baked);
      return;
    }
    var ctrl = typeof AbortController !== "undefined" ? new AbortController() : null;
    var timer = setTimeout(function () {
      if (ctrl) ctrl.abort();
    }, 8000);
    fetch("/api/wolf/shell-whoami?t=" + Date.now(), {
      credentials: "same-origin",
      signal: ctrl ? ctrl.signal : undefined,
      headers: { Accept: "application/json" }
    })
      .then(function (r) {
        return r.ok ? r.json() : null;
      })
      .catch(function () {
        return null;
      })
      .then(function (data) {
        clearTimeout(timer);
        if (data && data.ok && data.whoami) {
          /* Prefer parallel payload.nav_authority; keep whoami.nav_authority if only there. */
          if (data.nav_authority) {
            data.whoami.nav_authority = data.nav_authority;
          }
          if (data.outlet_children && !data.whoami.outlet_children) {
            data.whoami.outlet_children = data.outlet_children;
          }
          if (data.businesses && (!data.whoami.businesses || !data.whoami.businesses.length)) {
            data.whoami.businesses = data.businesses;
          }
          window.__WOLF_WHOAMI__ = data.whoami;
          cb(data.whoami);
        } else {
          cb(baked || { scoped: true, pages: [] });
        }
      });
  }

  function boot() {
    fetchWhoami(bootWith);
    window.addEventListener("resize", function () {
      applyMode();
      var who = whoami();
      var crumbs = document.getElementById("wolfnav-crumbs");
      if (crumbs && who) paintCrumbs(crumbs, who);
      syncNavHeight();
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }

  window.__WOLF_SHELL__ = {
    cache: CACHE,
    filterTree: filterTree,
    pageAllowed: pageAllowed,
    iaTree: IA_TREE,
    sameDest: sameDest,
    empireAliases: EMPIRE_ALIASES,
    crumbsFor: crumbsFor,
    businessesFor: businessesFor,
    navBizSource: navBizSource,
    paintBusiness: paintBusiness,
    parentHref: parentHref,
    backHref: backHref,
    homeHref: homeHref,
    hiddenSpecialistPrimary: HIDDEN_SPECIALIST_PRIMARY,
    /* Permissions Audience — chrome reads whoami.chain / whoami.permissions only. */
    canLayer: function (who, surface, layer) {
      who = who || whoami();
      var perms = (who && who.permissions) || ((who && who.chain) || {}).permissions || {};
      var surfaces = perms.surfaces || {};
      var row = surfaces[surface] || {};
      return !!row[layer];
    }
  };
})();

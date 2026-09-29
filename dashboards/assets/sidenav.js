/* sidenav.js — Beta Wave 1–8 + RHC V1 + Perms + Route Merge/Retire (#wolfnav).
 * One chrome owner. Never a second Boards menu.
 * IA: HOME / BUSINESSES / INTELLIGENCE / SYSTEM (Target IA 2026-09-22).
 * Wave 2: Owner HOME primary = Empire; /wolf alias → Empire; Progress under SYSTEM only.
 * Wave 3: BZG crumbs WOLF › Blu Zone › Uma Blu › Today; Devi landing Uma Today.
 * Wave 4: GGV crumbs WOLF › Goss Group › GGV › …; Amanda landing GGV Overview.
 * Wave 5: AMG crumbs WOLF › Atrium Management › AMG › …; Coral landing AMG Today.
 * Wave 6: Intel crumbs WOLF › Intelligence › …; Content under Intel; Haikal → Content.
 * Wave 7: System crumbs WOLF › System › …; Progress soft-land; Sale under SYSTEM;
 *   Factory EMPTY; staff hide SYSTEM admin via nav.
 * Wave 8: trading/travel/spartacus/mila/amanda/kuta-rates NOT in primary IA
 *   (Hidden ≠ deleted; soft redirect → /wolf). No new sprawl.
 * RHC V1: breadcrumbs · UP / BACK / HOME · multi-assignment context switcher;
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

  var CACHE = "20260922-nav-route-merge";
  var EMPIRE_ALIASES = { "/owner-empire-pack": 1, "/wolf": 1 };
  var TRAIL_KEY = "wolf-shell-trail";
  /* Wave 8 — retired from primary Boards; soft-redirect handled server-side. */
  var HIDDEN_SPECIALIST_PRIMARY = {
    trading: 1,
    travel: 1,
    spartacus: 1,
    mila: 1,
    amanda: 1,
    "kuta-rates": 1
  };

  var IA_TREE = [
    {
      id: "home",
      title: "HOME",
      items: [
        {
          href: "/owner-empire-pack",
          title: "Empire Pulse",
          key: "empire",
          primary: true,
          aliases: ["/wolf"]
        },
        { href: "/staff-ops-routing", title: "Needs You", key: "needs_you" }
      ]
    },
    {
      id: "businesses",
      title: "BUSINESSES",
      items: [
        { href: "/ggv-ops-pack", title: "GGV", key: "ggv" },
        { href: "/amg-ops-pack", title: "Atrium / AMG", key: "amg" },
        { href: "/bzg", title: "Blu Zone / BZG", key: "bzg" },
        { href: "/bzg/uma-blu", title: "Uma Blu · Today", key: "uma" }
      ]
    },
    {
      id: "intelligence",
      title: "INTELLIGENCE",
      items: [
        { href: "/intel-ops-pack", title: "Intelligence Home", key: "intel" },
        { href: "/content-2.0", title: "Content", key: "content" }
      ]
    },
    {
      id: "system",
      title: "SYSTEM",
      items: [
        { href: "/progress", title: "Progress", key: "progress" },
        { href: "/integration-health", title: "Integrations", key: "integrations" },
        { href: "/sale-evidence-pack", title: "Sale Readiness", key: "sale" }
      ]
    }
  ];

  /* Mirror of wolf_shell.ROUTE_PARENT / ROUTE_CRUMBS */
  var ROUTE_PARENT = {
    "/owner-empire-pack": null,
    "/wolf": null,
    "/staff-ops-routing": "/owner-empire-pack",
    "/ggv-ops-pack": "/owner-empire-pack",
    "/habitat-operator": "/ggv-ops-pack",
    "/lead-spine": "/ggv-ops-pack",
    "/amg-ops-pack": "/owner-empire-pack",
    "/amg-daily-ops-state": "/amg-ops-pack",
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
    "/sale-evidence-pack": "/progress"
  };

  var ROUTE_CRUMBS = {
    "/owner-empire-pack": [
      { label: "HOME", href: "/wolf" },
      { label: "Empire Pulse", href: null }
    ],
    "/wolf": [
      { label: "HOME", href: "/wolf" },
      { label: "Empire Pulse", href: null }
    ],
    "/staff-ops-routing": [
      { label: "HOME", href: "/wolf" },
      { label: "Needs You", href: null }
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
          esc(a.label) +
          " · " +
          esc(a.scope) +
          "</option>"
        );
      })
      .join("");
    el.innerHTML =
      '<label class="nv-ctx-label" for="wolfnav-ctx-select">Context</label>' +
      '<select id="wolfnav-ctx-select" class="nv-ctx-select" aria-label="Authorised context switcher">' +
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

    var ctx = document.getElementById("wolfnav-ctx");
    if (!ctx) {
      ctx = document.createElement("div");
      ctx.className = "nv-ctx";
      ctx.id = "wolfnav-ctx";
      ctx.hidden = true;
      row.insertBefore(ctx, crumbs.nextSibling);
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
      /* Owner / debug: codes may stay (audience · ROLE-*). */
      var roleHint = roleForActiveContext(who);
      var ownerLabel = name || (who && who.role_label) || "";
      if (ownerLabel && aud && roleHint) {
        hello.textContent = ownerLabel + " · " + aud + " · " + roleHint;
      } else if (ownerLabel && aud) {
        hello.textContent = ownerLabel + " · " + aud;
      } else if (ownerLabel) {
        hello.textContent = String(ownerLabel);
      } else {
        hello.textContent = "";
      }
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

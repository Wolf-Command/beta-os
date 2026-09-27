/* Shared truth strip. One vocabulary. No second navigation. */
(function () {
  var STATES = ["LIVE", "CURRENT", "STALE", "UNKNOWN", "UNAVAILABLE", "NEEDS REVIEW"];

  function esc(value) {
    return String(value == null ? "" : value).replace(/[&<>"']/g, function (ch) {
      return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[ch];
    });
  }

  function stateClass(state) {
    return "wolf-state wolf-state-" + String(state || "UNKNOWN").toLowerCase().replace(/\s+/g, "-");
  }

  function chip(state) {
    var label = STATES.indexOf(state) >= 0 ? state : "UNKNOWN";
    return '<span class="' + stateClass(label) + '" data-display-state="' + esc(label) + '">' + esc(label) + "</span>";
  }

  function empty(text) {
    return '<div class="wolf-empty" data-state="empty">' + esc(text || "Nothing is here. Empty is not unknown.") + "</div>";
  }

  function errorBox(text) {
    return '<div class="wolf-error" data-state="error">' + esc(text || "This could not be loaded. Nothing was invented.") + "</div>";
  }

  function denied(text) {
    return '<div class="wolf-denied" data-state="permission-denied">' + esc(text || "You do not have access to this.") + "</div>";
  }

  function card(title, body) {
    return '<article class="wolf-card"><h3>' + esc(title) + "</h3>" + body + "</article>";
  }

  function ensureStyle() {
    if (document.getElementById("wolf-truth-style")) return;
    var link = document.querySelector('link[href*="wolf-truth.css"]');
    if (link) return;
    var style = document.createElement("style");
    style.id = "wolf-truth-style";
    style.textContent = ".wolf-truth{margin:12px 0}.wolf-card{border:1px solid rgba(138,166,166,.35);border-radius:12px;padding:12px;margin-top:8px}.wolf-state{display:inline-flex;align-items:center;min-height:28px;padding:2px 8px;border-radius:999px;border:1px solid rgba(138,166,166,.45);font-size:.75rem;font-weight:700}.wolf-empty,.wolf-error,.wolf-denied{margin-top:8px;font-size:.88rem}.wolf-truth a{min-height:44px;display:inline-flex;align-items:center}";
    document.head.appendChild(style);
  }

  function render(el, data) {
    var sources = data.sources || [];
    var html = '<div class="wolf-truth">';
    html += "<h2>Data truth</h2>";
    if (data.surface === "empire" || el.getAttribute("data-mode") === "registry") {
      html += '<p><a href="/dashboard-truth">Open the source register</a></p>';
    }
    sources.forEach(function (row) {
      var body = chip(row.display_state) + "<p>" + esc(row.plain || "") + "</p>";
      if (row.commissioned !== true) {
        body += "<p>Not commissioned.</p>";
      }
      if (row.presence === "EMPTY") {
        body += empty("Nothing is here. Empty is not unknown.");
      }
      if (row.historical_cut) {
        body += "<p>" + esc(row.historical_cut) + "</p>";
      }
      html += card(row.name || row.source_id || "Source", body);
    });
    if (!sources.length) {
      html += empty("No source was returned. That is empty, not a zero.");
    }
    html += "</div>";
    el.innerHTML = html;
  }

  function mount(el) {
    ensureStyle();
    var surface = el.getAttribute("data-surface") || "my-work";
    var mode = el.getAttribute("data-mode") || "stamp";
    var url = mode === "registry"
      ? "/api/dashboard-truth"
      : "/api/dashboard-truth/stamp?surface=" + encodeURIComponent(surface);
    fetch(url, { headers: { Accept: "application/json" } })
      .then(function (res) {
        return res.json().catch(function () { return {}; }).then(function (data) {
          return { status: res.status, data: data };
        });
      })
      .then(function (pack) {
        var data = pack.data || {};
        if (pack.status === 403 || (data.ui && data.ui.component === "permission-denied")) {
          el.innerHTML = '<div class="wolf-truth">' + denied((data.ui && data.ui.message) || data.message) + "</div>";
          return;
        }
        if (!pack.status || pack.status >= 400 || data.ok === false) {
          el.innerHTML = '<div class="wolf-truth">' + errorBox(data.message) + "</div>";
          return;
        }
        render(el, data);
      })
      .catch(function () {
        el.innerHTML = '<div class="wolf-truth">' + errorBox() + "</div>";
      });
  }

  function boot() {
    document.querySelectorAll("[data-wolf-truth]").forEach(mount);
  }

  window.WolfTruth = {
    STATES: STATES,
    chip: chip,
    empty: empty,
    error: errorBox,
    denied: denied,
    card: card,
    mount: mount
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();

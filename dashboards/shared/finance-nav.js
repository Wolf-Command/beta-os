(function () {
  "use strict";

  var root = document.getElementById("wolf-finance-nav");
  if (!root) return;

  var entity = root.getAttribute("data-entity") || "ENT-GGV";

  function esc(text) {
    return String(text == null ? "" : text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function currentPath() {
    return (window.location.pathname || "/").replace(/\/$/, "") || "/";
  }

  function areaForPath(areas, path) {
    var found = null;
    (areas || []).forEach(function (area) {
      (area.items || []).forEach(function (item) {
        var href = (item.href || "").split("?")[0].replace(/\/$/, "");
        if (href && (path === href || path.indexOf(href + "/") === 0)) {
          found = area.label;
        }
      });
    });
    return found || (areas[0] && areas[0].label) || "Overview";
  }

  function render(data, activeLabel) {
    var areas = data.areas || [];
    var active = null;
    areas.forEach(function (area) {
      if (area.label === activeLabel) active = area;
    });
    if (!active) active = areas[0];
    var company = data.company_label || data.entity_id || "";
    var books = data.books_file ? "Books file " + data.books_file + ". Companies stay separate." : "";
    var primary = areas.map(function (area) {
      var current = area.label === (active && active.label) ? ' aria-current="true"' : "";
      return '<li><button type="button" data-area="' + esc(area.label) + '"' + current + ">" + esc(area.label) + "</button></li>";
    }).join("");
    var items = (active && active.items) || [];
    var path = currentPath();
    var secondary = items.length
      ? items.map(function (item) {
          var href = item.href || "#";
          var here = path === href.replace(/\/$/, "") ? ' aria-current="page"' : "";
          var title = item.note ? ' title="' + esc(item.note) + '"' : "";
          return '<li><a href="' + esc(href) + '"' + here + title + ">" + esc(item.label) + "</a></li>";
        }).join("")
      : '<li><span class="wfn-note">' + esc((active && active.empty_note) || "Nothing in this area for this assignment.") + "</span></li>";
    var note = "";
    items.forEach(function (item) {
      if (item.note && path === String(item.href || "").replace(/\/$/, "")) note = item.note;
    });
    root.innerHTML =
      '<p class="wfn-company">' + esc(company) + (books ? " · " + esc(books) : "") + "</p>" +
      '<ul class="wfn-primary">' + primary + "</ul>" +
      '<ul class="wfn-secondary">' + secondary + "</ul>" +
      (note ? '<p class="wfn-note">' + esc(note) + "</p>" : "");
    root.querySelectorAll("button[data-area]").forEach(function (button) {
      button.addEventListener("click", function () {
        render(data, button.getAttribute("data-area"));
      });
    });
    document.body.classList.add("wolf-finance-unified");
  }

  fetch("/api/finance/nav?entity=" + encodeURIComponent(entity), {
    credentials: "same-origin",
    headers: { Accept: "application/json" },
  })
    .then(function (res) {
      return res.json().then(function (body) {
        if (!res.ok || !body || body.ok === false) {
          throw new Error((body && body.message) || "Finance navigation unavailable");
        }
        return body;
      });
    })
    .then(function (body) {
      render(body, areaForPath(body.areas || [], currentPath()));
    })
    .catch(function () {
      /* The existing company navigation stays in place. */
    });
})();

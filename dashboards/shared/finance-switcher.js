(function () {
  "use strict";

  var STORAGE_KEY = "wolf.finance.entity";

  function esc(text) {
    return String(text || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/"/g, "&quot;");
  }

  function rememberEntity(id) {
    if (!id) return;
    try {
      localStorage.setItem(STORAGE_KEY, id);
    } catch (_err) {
      /* ignore */
    }
  }

  function render(container, entities, currentId) {
    if (!container) return;
    var html = '<label class="wfs-label" for="wolf-finance-entity-select">BUSINESS</label>';
    html += '<select id="wolf-finance-entity-select" class="wfs-select" aria-label="BUSINESS">';
    (entities || []).forEach(function (row) {
      var selected = row.id === currentId ? " selected" : "";
      var disabled = row.selectable ? "" : " disabled";
      var title = row.selectable ? "" : ' title="NO ACCESS"';
      var suffix = row.selectable ? "" : " — NO ACCESS";
      html +=
        '<option value="' +
        esc(row.id) +
        '"' +
        selected +
        disabled +
        title +
        ">" +
        esc(row.label || row.id) +
        suffix +
        "</option>";
    });
    html += "</select>";
    container.innerHTML = html;
    container.classList.add("wolf-finance-switcher-mounted");

    var select = container.querySelector("#wolf-finance-entity-select");
    if (!select) return;

    select.addEventListener("change", function () {
      var entity = (entities || []).find(function (row) {
        return row.id === select.value;
      });
      if (!entity || !entity.selectable) {
        select.value = currentId;
        return;
      }
      rememberEntity(entity.id);
      if (entity.href) window.location.href = entity.href;
    });
  }

  function loadEntities() {
    return fetch("/api/finance/entities", {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
    }).then(function (res) {
      return res.json().then(function (body) {
        if (!res.ok) throw new Error(body.message || "Finance entities unavailable");
        return body.entities || body.finance_entities || [];
      });
    });
  }

  window.WolfFinanceSwitcher = {
    mount: function (container, options) {
      options = options || {};
      render(container, options.entities || [], options.currentEntityId || options.current || "GGV");
    },
    loadAndMount: function (container, currentId) {
      return loadEntities().then(function (entities) {
        render(container, entities, currentId);
        return entities;
      });
    },
    rememberEntity: rememberEntity,
  };

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("[data-wolf-finance-switcher]").forEach(function (el) {
      var current = el.getAttribute("data-current") || "GGV";
      window.WolfFinanceSwitcher.loadAndMount(el, current);
    });
  });
})();

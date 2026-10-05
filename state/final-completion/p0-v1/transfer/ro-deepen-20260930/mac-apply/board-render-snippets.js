/* Beta Owner Trading/Fitness RO board fillers.
 * Graft into owner-trading-1.html / owner-fitness-1.html.
 * Fail-closed: shows "no SoT yet" / error stamps. Never invents holdings.
 */
async function loadOwnerTradingRO(el) {
  const root = typeof el === "string" ? document.querySelector(el) : el;
  if (!root) return;
  root.innerHTML = "<p class='muted'>Loading V1 trading RO…</p>";
  try {
    const r = await fetch("/api/owner/trading-ro", { credentials: "same-origin" });
    const j = await r.json();
    if (!j.ok && j.reason === "NO_SOT_YET") {
      root.innerHTML =
        "<div class='honesty'><strong>no SoT yet</strong> — V1 trading-desk / holdings not reachable. " +
        "Paper only. No live broker. Nothing invented.</div>";
      return;
    }
    const h = j.holdings || {};
    const jr = j.journal || {};
    const docs = (j.paper_quant_docs || []).join(", ") || "none";
    root.innerHTML = [
      "<div class='honesty'>" + (j.banner || "Paper only") + "</div>",
      "<ul>",
      "<li>Holdings: <strong>" + (h.holdings_status || "?") + "</strong> count=" + (h.holdings_count ?? 0) + "</li>",
      "<li>Journal rows: <strong>" + (jr.journal_rows ?? 0) + "</strong> (" + (jr.journal_status || "?") + ")</li>",
      "<li>Paper quant docs: " + docs + "</li>",
      "<li>staff_ready=false · live_broker=false · " + (j.claim || "") + "</li>",
      "</ul>",
      jr.journal_sample && jr.journal_sample.length
        ? "<pre class='sample'>" + JSON.stringify(jr.journal_sample, null, 2) + "</pre>"
        : "<p class='muted'>No journal sample.</p>",
    ].join("");
  } catch (e) {
    root.innerHTML =
      "<div class='honesty error'>Trading RO fetch failed — fail closed. " +
      String(e) +
      "</div>";
  }
}

async function loadOwnerFitnessRO(el) {
  const root = typeof el === "string" ? document.querySelector(el) : el;
  if (!root) return;
  root.innerHTML = "<p class='muted'>Loading V1 Spartacus RO…</p>";
  try {
    const r = await fetch("/api/owner/fitness-ro", { credentials: "same-origin" });
    const j = await r.json();
    if (!j.ok && j.reason === "NO_SOT_YET") {
      root.innerHTML =
        "<div class='honesty'><strong>no SoT yet</strong> — spartacus.sqlite not reachable. " +
        "Fitness ≠ HR. No invented workouts.</div>";
      return;
    }
    const counts = j.table_counts || {};
    const keys = ["training_log", "lift_sessions", "days", "water_log", "habits"];
    const countLine = keys
      .map((k) => k + "=" + (counts[k] == null ? "—" : counts[k]))
      .join(" · ");
    const workouts = (j.recent_workouts || [])
      .map((w) => "<li>" + (w.date || "?") + " — " + (w.lift || "?") + "</li>")
      .join("");
    root.innerHTML = [
      "<div class='honesty'>" + (j.banner || "Fitness RO") + "</div>",
      "<p>Table counts (subset): " + countLine + "</p>",
      "<p>Days w/ workout: " + ((j.day_stats && j.day_stats.days_with_wo) ?? "—") +
        " · closed: " + ((j.day_stats && j.day_stats.days_closed) ?? "—") + "</p>",
      "<p>Recent workouts (date/lift only, no PII):</p>",
      workouts ? "<ul>" + workouts + "</ul>" : "<p class='muted'>None.</p>",
      "<p class='muted'>staff_ready=false · " + (j.claim || "") + "</p>",
    ].join("");
  } catch (e) {
    root.innerHTML =
      "<div class='honesty error'>Fitness RO fetch failed — fail closed. " +
      String(e) +
      "</div>";
  }
}

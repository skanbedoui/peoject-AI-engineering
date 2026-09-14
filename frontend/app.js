const $ = (id) => document.getElementById(id);
const colors = ["#378966", "#5686bd", "#d48b70"];
const names = {
  baseline: "Baseline",
  "top-local": "Top-local replacement",
  "cheap-local": "Cheap-local replacement",
};
let data,
  models = [],
  clauses = [],
  requestId = 0;
const escape = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const number = (n, decimals = 0) =>
  Number(n).toLocaleString(undefined, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
const ok = (row) => row?.correct === "True";
const prediction = (row) =>
  row?.parsed || (row ? "Invalid output" : "Unavailable");
async function get(url) {
  const response = await fetch(url);
  const result = await response.json();
  if (!response.ok) throw Error(result.error || "Unable to load results");
  return result;
}
function setView(view) {
  $("overview").hidden = view !== "overview";
  $("explorer").hidden = view !== "explorer";
  document
    .querySelectorAll(".tab")
    .forEach((button) =>
      button.classList.toggle("active", button.dataset.view === view),
    );
}
document
  .querySelectorAll(".tab")
  .forEach((button) => (button.onclick = () => setView(button.dataset.view)));
function render() {
  models = data.models.map((model, index) => ({
    ...model,
    color: colors[index % colors.length],
    byId: new Map(model.items.map((row) => [row.id, row])),
  }));
  const currentClauses = new Map(data.items.map((item) => [item.id, item]));
  const rows = new Map();
  models.forEach((model) =>
    model.items.forEach((row) => {
      if (!rows.has(row.id))
        rows.set(row.id, {
          id: row.id,
          expected: row.expected,
          clause:
            currentClauses.get(row.id)?.clause || "Clause text unavailable",
        });
    }),
  );
  clauses = [...rows.values()];
  $("dataset-count").textContent =
    `${clauses.length} clauses / ${models.length} models`;
  $("run-foot").textContent = `RUN ${data.run}`;
  $("row-count").title =
    data.clause_source === "current_dataset"
      ? "Legacy run: clause text comes from the current dataset."
      : "Clause text saved with this run.";
  $("model-cards").innerHTML = models
    .map((model) => {
      const s = model.summary;
      const accuracy = Number(s.accuracy) * 100;
      return `<article class="model" style="--color:${model.color}"><div class="model-heading"><div><span class="role">${escape(names[s.profile] || s.profile)}</span><h2>${escape(s.model)}</h2></div>${Number(s.accuracy) === Math.max(...models.map((m) => Number(m.summary.accuracy))) ? '<span class="badge">BEST ACCURACY</span>' : ""}</div><div class="accuracy">${number(accuracy)}<small>%</small></div><div class="support">${escape(s.correct)} of ${escape(s.items)} clauses correct</div><div class="mini-track"><i style="width:${accuracy}%"></i></div><div class="stats"><div><strong>${number(Number(s.p50_latency_ms) / 1000, 2)} s</strong><span>Median latency</span></div><div><strong>${number(s.output_tokens_per_second, 1)}</strong><span>Tokens / second</span></div><div><strong>${escape(s.parse_errors)}</strong><span>Parse errors</span></div></div></article>`;
    })
    .join("");
  $("accuracy-chart").innerHTML =
    models
      .map((model) =>
        bar(
          model,
          Number(model.summary.accuracy) * 100,
          100,
          `${number(Number(model.summary.accuracy) * 100)}%`,
        ),
      )
      .join("") +
    '<div class="axis"><span>0%</span><span>25%</span><span>50%</span><span>75%</span><span>100%</span></div>';
  metricChart();
  const categories = [...new Set(clauses.map((c) => c.expected))].sort();
  document.querySelector(".category-section .section-title p").textContent =
    models.map((m) => m.summary.model).join(" / ");
  $("category").innerHTML =
    '<option value="">All categories</option>' +
    categories.map((c) => `<option>${escape(c)}</option>`).join("");
  $("category-grid").innerHTML = categories
    .map(
      (category) =>
        `<div class="category-item"><span>${escape(category)}</span>${models
          .map((model) => {
            const rows = model.items.filter((row) => row.expected === category);
            const count = rows.filter(ok).length;
            const rate = rows.length ? count / rows.length : 0;
            return `<button class="heat" data-category="${escape(category)}" title="${escape(model.summary.model)}: ${count}/${rows.length} correct" aria-label="${escape(category)}, ${escape(model.summary.model)}: ${count}/${rows.length} correct" style="background:${rate === 1 ? "#347f60" : rate > 0 ? "#98c9b0" : "#e6e9ed"};color:${rate === 1 ? "white" : "#55645d"}">${count}/${rows.length}</button>`;
          })
          .join("")}</div>`,
    )
    .join("");
  $("category-grid")
    .querySelectorAll("button")
    .forEach(
      (button) =>
        (button.onclick = () => {
          $("category").value = button.dataset.category;
          $("search").value = "";
          $("outcome").value = "all";
          setView("explorer");
          table();
        }),
    );
  $("table-head").innerHTML =
    `<tr><th>CLAUSE / EXPECTED CATEGORY</th>${models.map((m) => `<th style="color:${m.color}">${escape(m.summary.model)}</th>`).join("")}</tr>`;
  table();
}
function bar(model, value, max, label, sub = "") {
  return `<div class="bar-row"><div class="bar-label">${escape(model.summary.model.replace("llama", "Llama "))}${sub ? `<small>${escape(sub)}</small>` : ""}</div><div class="bar-track"><div class="bar-fill" style="--color:${model.color};width:${Math.min(100, (value / max) * 100)}%"></div></div><b>${escape(label)}</b></div>`;
}
function metricChart() {
  const metric = $("metric").value;
  let key, suffix, subtitle, title;
  if (metric === "latency") {
    key = "p50_latency_ms";
    suffix = " s";
    title = "Response latency";
    subtitle = "Median / p95 in seconds; startup included";
  } else if (metric === "throughput") {
    key = "output_tokens_per_second";
    suffix = " tok/s";
    title = "Generation speed";
    subtitle = "Generated tokens / generation duration";
  } else {
    key = "measured_requests_per_hour";
    suffix = " /h";
    title = "Measured throughput";
    subtitle = "Sequential requests per hour, including startup";
  }
  $("metric-title").textContent = title;
  $("metric-subtitle").textContent = subtitle;
  const max = Math.max(...models.map((m) => Number(m.summary[key])), 1) * 1.15;
  $("metric-chart").innerHTML = models
    .map((m) => {
      const n = Number(m.summary[key]);
      return bar(
        m,
        n,
        max,
        number(
          metric === "latency" ? n / 1000 : n,
          metric === "requests" ? 0 : 2,
        ) + suffix,
        metric === "latency"
          ? `p95 ${number(Number(m.summary.p95_latency_ms) / 1000, 2)} s`
          : "",
      );
    })
    .join("");
}
function table() {
  const query = $("search").value.trim().toLowerCase(),
    category = $("category").value,
    outcome = $("outcome").value;
  const filtered = clauses.filter((item) => {
    const results = models.map((m) => m.byId.get(item.id));
    return (
      (!query ||
        `${item.id} ${item.clause} ${item.expected}`
          .toLowerCase()
          .includes(query)) &&
      (!category || item.expected === category) &&
      (outcome === "all" ||
        (outcome === "wrong" && results.some((r) => !ok(r))) ||
        (outcome === "correct" && results.every(ok)) ||
        (outcome === "parse" &&
          results.some((r) => r?.status === "parse_error")))
    );
  });
  $("row-count").textContent =
    `${filtered.length} of ${clauses.length} clauses`;
  $("empty").hidden = !!filtered.length;
  $("table-body").innerHTML = filtered
    .map(
      (item) =>
        `<tr><td><button class="clause-link" data-id="${escape(item.id)}"><strong>${escape(item.id)} &nbsp; ${escape(item.expected)}</strong><small>${escape(item.clause.length > 95 ? item.clause.slice(0, 95) + "..." : item.clause)}</small></button></td>${models
          .map((model) => {
            const row = model.byId.get(item.id);
            return `<td class="${ok(row) ? "success" : "failure"}"><span class="pill"></span>${escape(prediction(row))}<small>${row ? number(Number(row.latency_ms) / 1000, 2) + " s" : "No result"}</small></td>`;
          })
          .join("")}</tr>`,
    )
    .join("");
  $("table-body")
    .querySelectorAll("button")
    .forEach((button) => (button.onclick = () => detail(button.dataset.id)));
}
function detail(id) {
  const item = clauses.find((c) => c.id === id);
  $("detail-id").textContent = `CLAUSE ${id}`;
  $("detail-title").textContent = item.expected;
  $("detail-clause").textContent = item.clause;
  $("detail-models").innerHTML = models
    .map((model) => {
      const row = model.byId.get(id);
      return `<div class="detail-model"><strong>${escape(model.summary.model)}</strong> <span class="${ok(row) ? "success" : "failure"}">${ok(row) ? "Correct" : "Incorrect"}</span><pre>${escape(row?.output || "No output")}</pre><div class="muted">${escape(row?.status || "Unavailable")} · ${row ? number(Number(row.latency_ms) / 1000, 2) + " s" : ""}${row?.error ? " · " + escape(row.error) : ""}</div></div>`;
    })
    .join("");
  $("detail").showModal();
}
$("close").onclick = () => $("detail").close();
$("detail").onclick = (event) => {
  if (event.target === $("detail")) {
    const r = $("detail").getBoundingClientRect();
    if (
      event.clientX < r.left ||
      event.clientX > r.right ||
      event.clientY < r.top ||
      event.clientY > r.bottom
    )
      $("detail").close();
  }
};
$("metric").onchange = metricChart;
["search", "category", "outcome"].forEach((id) =>
  $(id).addEventListener("input", table),
);
$("export").onclick = () => {
  if (!data) return;
  const rows = data.models.map((m) => m.summary),
    keys = Object.keys(rows[0]);
  const cell = (value) => '"' + String(value ?? "").replaceAll('"', '""') + '"';
  const csv = [keys, ...rows.map((r) => keys.map((k) => r[k]))]
    .map((row) => row.map(cell).join(","))
    .join("\r\n");
  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = `comparison-${data.run}.csv`;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
};
async function load() {
  const id = ++requestId;
  $("message").hidden = false;
  $("message").textContent = "Loading benchmark results...";
  $("content").hidden = true;
  try {
    const result = await get(
      "/api/run?id=" + encodeURIComponent($("run").value),
    );
    if (id !== requestId) return;
    data = result;
    if (!data.models.length)
      throw Error("This run has no completed models yet.");
    render();
    $("content").hidden = false;
    $("message").hidden = true;
  } catch (error) {
    if (id === requestId) $("message").textContent = error.message;
  }
}
$("run").onchange = load;
(async () => {
  try {
    const list = await get("/api/runs");
    if (!list.length)
      throw Error(
        "No saved comparisons found. Run python src/run.py --compare first.",
      );
    $("run").innerHTML = list
      .map(
        (id) =>
          `<option value="${escape(id)}">${escape(id.slice(0, 4) + "-" + id.slice(4, 6) + "-" + id.slice(6, 8) + " / " + id.slice(9, 11) + ":" + id.slice(11, 13) + " UTC")}</option>`,
      )
      .join("");
    await load();
  } catch (error) {
    $("message").textContent = error.message;
  }
})();

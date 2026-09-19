const navigationGroups = [
  ["Operations", [
    ["command-center", "Command center", "⌂"], ["disruptions", "Disruptions", "!"],
    ["supply-network", "Supply network", "◇"], ["suppliers", "Suppliers", "◎"],
    ["inventory", "Inventory", "▦"], ["shipments", "Shipments", "↗"],
  ]],
  ["Decisioning", [
    ["scenarios", "Scenarios", "≋"], ["recommendations", "Recommendations", "✦"],
    ["approvals", "Approvals", "✓"], ["executions", "Executions", "▶"],
  ]],
  ["Control plane", [
    ["workflows", "Workflows", "⌘"], ["simulations", "Simulations", "◉"],
    ["integrations", "Integrations", "⚙"], ["audit", "Audit", "≡"],
  ]],
];

const incidents = [
  { title: "Typhoon disrupts southern Taiwan semiconductor capacity", source: "Global Weather · Tainan, Taiwan", severity: "CRITICAL", status: "ASSESSED", risk: "0.91", exposure: "₹4.82 Cr", age: "18 min" },
  { title: "Singapore port congestion extends container dwell time", source: "Trusted News · Singapore", severity: "HIGH", status: "MONITORING", risk: "0.76", exposure: "₹1.14 Cr", age: "1 hr" },
  { title: "Penang battery supplier reports reduced weekly output", source: "Supplier Feed · Penang, Malaysia", severity: "MEDIUM", status: "OPEN", risk: "0.58", exposure: "₹38.6 L", age: "3 hr" },
  { title: "Shipment TRK-NOVA-90012 delayed at transshipment hub", source: "Ocean Tracking · Colombo", severity: "MEDIUM", status: "OPEN", risk: "0.49", exposure: "₹22.1 L", age: "5 hr" },
];

const suppliers = [
  ["Formosa Silicon Works", "Tainan, Taiwan", "Semiconductors", "CRITICAL", "₹4.82 Cr", "96"],
  ["Hanseong Semiconductors", "Icheon, South Korea", "Semiconductors", "GOOD", "₹1.28 Cr", "88"],
  ["Kyoto Battery Systems", "Kyoto, Japan", "Battery systems", "GOOD", "₹82.4 L", "94"],
  ["Singapore Storage Systems", "Singapore", "Storage", "HIGH", "₹61.8 L", "77"],
  ["Deccan Precision Circuits", "Hyderabad, India", "PCB", "MEDIUM", "₹44.2 L", "74"],
];

const inventory = [
  ["CPU-X9", "X9 Performance Processor", "Bengaluru Plant", "312", "11 days", "CRITICAL"],
  ["CPU-U7", "U7 Mobile Processor", "Chennai Plant", "584", "19 days", "HIGH"],
  ["PWR-IC-42", "Power Management IC", "Pune DC", "1,840", "24 days", "MEDIUM"],
  ["DRAM-16", "16 GB LPDDR5 Module", "Bengaluru Plant", "2,108", "42 days", "GOOD"],
  ["PANEL-14", "14-inch High Resolution Panel", "Mumbai DC", "719", "36 days", "GOOD"],
];

const workflowStages = ["Detect disruption", "Assess impact", "Score risk", "Generate scenarios", "Recommend action", "Route approval", "Execute mitigation", "Verify outcome"];

const state = { approval: "PENDING", execution: "PENDING", simulation: -1, simulationTimer: null };

function status(value) {
  const key = value.toLowerCase().replaceAll("_", "-");
  return `<span class="status ${key}">${value.replaceAll("_", " ")}</span>`;
}

function pageHead(eyebrow, title, description, action = "") {
  return `<header class="page-head"><div><p class="eyebrow">${eyebrow}</p><h1>${title}</h1><p class="page-subtitle">${description}</p></div>${action}</header>`;
}

function metrics(items) {
  return `<section class="metrics">${items.map(([label, value, detail, delta = ""]) => `<article class="card metric searchable"><div class="metric-label">${label}</div><div class="metric-value">${value}${delta ? `<span class="delta">${delta}</span>` : ""}</div><div class="metric-detail">${detail}</div></article>`).join("")}</section>`;
}

function commandCenter() {
  return `${pageHead("Command center", "Operate ahead of disruption.", "A connected decision workspace for signals, deterministic impact analysis, mitigation choices, and governed action.", `<button class="button" data-go="scenarios">Review mitigation →</button>`)}
    ${metrics([["Active incidents", "4", "Two require a decision in the next four hours.", "+1"], ["Revenue at risk", "₹6.57 Cr", "Calculated from 42 affected customer orders."], ["Protected by plans", "₹5.12 Cr", "Expected protection from recommended scenarios."], ["Open approvals", "1", "Alternate source activation awaits approval."]])}
    <section class="grid-2">
      <article class="card panel searchable"><div class="card-heading"><div><h2>Priority disruption</h2><p>Highest composite business-risk score</p></div>${status("CRITICAL")}</div><div class="focus-incident"><small class="eyebrow">INC-2026-0915-01</small><h3>Typhoon disrupts southern Taiwan semiconductor capacity</h3><p>Formosa Silicon Works has suspended Tainan operations. CPU-X9 and CPU-U7 supply is exposed across two finished-product families.</p><div class="facts"><div class="fact"><span>Stockout</span><strong>11 days</strong></div><div class="fact"><span>Orders</span><strong>18 affected</strong></div><div class="fact"><span>Confidence</span><strong>94%</strong></div></div></div></article>
      <article class="card panel searchable"><div class="card-heading"><div><h2>Risk distribution</h2><p>Open incident portfolio</p></div><span class="status good">LIVE MODEL</span></div><div class="risk-bars"><div class="bar-row"><span>Critical</span><div class="bar critical"><span style="width:25%"></span></div><strong>1</strong></div><div class="bar-row"><span>High</span><div class="bar high"><span style="width:50%"></span></div><strong>1</strong></div><div class="bar-row"><span>Medium</span><div class="bar"><span style="width:75%"></span></div><strong>2</strong></div><div class="bar-row"><span>Low</span><div class="bar"><span style="width:0"></span></div><strong>0</strong></div></div></article>
    </section>
    <section class="grid-even">
      <article class="card panel searchable"><div class="card-heading"><div><h2>Decision readiness</h2><p>Current Taiwan incident response</p></div>${status("APPROVAL READY")}</div><div class="timeline"><div class="timeline-item"><span class="timeline-dot"></span><span>Signal normalized and supplier matched</span><small>08:12</small></div><div class="timeline-item"><span class="timeline-dot"></span><span>Revenue and order exposure calculated</span><small>08:14</small></div><div class="timeline-item"><span class="timeline-dot"></span><span>Three feasible scenarios optimized</span><small>08:16</small></div><div class="timeline-item"><span class="timeline-dot"></span><span>Alternate-source plan recommended</span><small>08:17</small></div></div></article>
      <article class="card panel searchable"><div class="card-heading"><div><h2>Network pulse</h2><p>Nova Electronics tenant coverage</p></div>${status("HEALTHY")}</div><div class="facts"><div class="fact"><span>Suppliers</span><strong>18</strong></div><div class="fact"><span>Materials</span><strong>40</strong></div><div class="fact"><span>Facilities</span><strong>8</strong></div></div><p class="notice">944 connected demonstration records preserve supplier, material, BOM, order, shipment, signal, incident, and decision lineage.</p></article>
    </section>`;
}

function disruptions() {
  return `${pageHead("Operations", "Disruption intelligence", "Normalized operational signals grouped into explainable, tenant-scoped incidents.")}
  <section class="card table-wrap"><table><thead><tr><th>Incident</th><th>Severity</th><th>Status</th><th>Risk</th><th>Revenue exposure</th><th>Detected</th></tr></thead><tbody>${incidents.map(i => `<tr class="searchable"><td><strong>${i.title}</strong><small>${i.source}</small></td><td>${status(i.severity)}</td><td>${status(i.status)}</td><td><strong>${i.risk}</strong></td><td>${i.exposure}</td><td>${i.age}</td></tr>`).join("")}</tbody></table></section>`;
}

function supplyNetwork() {
  return `${pageHead("Operations", "Supply network", "Trace the Taiwan disruption from supplier sites through critical materials, plants, products, and customer demand.")}
  <section class="card network searchable"><div class="node n1"><strong>Formosa Silicon</strong><small>Tainan · disrupted</small></div><div class="node n2"><strong>Hanseong Semi</strong><small>Icheon · alternate</small></div><div class="node center"><strong>CPU-X9 / CPU-U7</strong><small>Critical processors</small></div><div class="node n3"><strong>Bengaluru Plant</strong><small>NovaBook Pro</small></div><div class="node n4"><strong>Chennai Plant</strong><small>NovaBook Air</small></div></section>
  <section class="grid-even"><article class="card panel"><div class="card-heading"><div><h2>Propagation path</h2><p>Deterministic multi-level BOM traversal</p></div>${status("4 HOPS")}</div><div class="timeline"><div class="timeline-item"><span class="timeline-dot"></span><span>Supplier site disruption</span><small>Formosa</small></div><div class="timeline-item"><span class="timeline-dot"></span><span>Processor material constraint</span><small>CPU-X9</small></div><div class="timeline-item"><span class="timeline-dot"></span><span>Finished product exposure</span><small>NovaBook Pro</small></div><div class="timeline-item"><span class="timeline-dot"></span><span>Customer order impact</span><small>18 orders</small></div></div></article><article class="card panel"><div class="card-heading"><div><h2>Concentration</h2><p>Current primary-source dependency</p></div>${status("HIGH")}</div>${metrics([["Formosa share", "62%", "Of Nova performance-processor allocation."], ["Alternate capacity", "38%", "Available through qualified sources."]]).replace('class="metrics"','class="grid-even"')}</article></section>`;
}

function dataTablePage(kind) {
  const isSupplier = kind === "suppliers";
  const rows = isSupplier ? suppliers : inventory;
  const title = isSupplier ? "Supplier resilience" : "Inventory coverage";
  const description = isSupplier ? "Monitor concentration, operational health, ratings, and incident-linked exposure." : "Prioritize constrained materials using inventory position and projected consumption.";
  const headers = isSupplier ? ["Supplier", "Location", "Category", "Health", "Exposure", "Rating"] : ["Material", "Description", "Location", "On hand", "Coverage", "Risk"];
  return `${pageHead("Operations", title, description)}<section class="card table-wrap"><table><thead><tr>${headers.map(h => `<th>${h}</th>`).join("")}</tr></thead><tbody>${rows.map(row => `<tr class="searchable">${row.map((cell, index) => `<td>${index === 0 ? `<strong>${cell}</strong>` : index === 3 || index === 5 ? (/[A-Z]/.test(cell) && !/^₹/.test(cell) && !/^\d/.test(cell) ? status(cell) : cell) : cell}</td>`).join("")}</tr>`).join("")}</tbody></table></section>`;
}

function shipments() {
  const rows = [["TRK-NOVA-90012", "Kaohsiung → Chennai", "CPU-X9 · 320 units", "DELAYED", "22 Sep"], ["TRK-NOVA-90008", "Busan → Mumbai", "DRAM-16 · 1,800 units", "IN TRANSIT", "19 Sep"], ["TRK-NOVA-90017", "Singapore → Chennai", "NVME-1TB · 640 units", "AT RISK", "24 Sep"], ["TRK-NOVA-90003", "Osaka → Bengaluru", "PWR-IC-42 · 2,400 units", "ON TIME", "18 Sep"]];
  return `${pageHead("Operations", "Shipment visibility", "Track inbound material movements and events tied to customer-order exposure.")}<section class="card table-wrap"><table><thead><tr><th>Tracking</th><th>Route</th><th>Cargo</th><th>Status</th><th>Expected</th></tr></thead><tbody>${rows.map(r => `<tr class="searchable"><td><strong>${r[0]}</strong></td><td>${r[1]}</td><td>${r[2]}</td><td>${status(r[3])}</td><td>${r[4]}</td></tr>`).join("")}</tbody></table></section>`;
}

function scenarios() {
  const cards = [
    ["Activate alternate source", "Shift urgent CPU-X9 volume to qualified Hanseong capacity.", "₹1.65 Cr", "7 days", "₹5.12 Cr", "0.89", true],
    ["Premium air freight", "Expedite available Formosa safety stock after operations resume.", "₹2.84 Cr", "5 days", "₹4.46 Cr", "0.76", false],
    ["Reallocate inventory", "Move processor stock from lower-priority regional allocations.", "₹48 L", "12 days", "₹3.21 Cr", "0.68", false],
  ];
  return `${pageHead("Decisioning", "Compare mitigation scenarios", "Feasible actions ranked against protected revenue, incremental cost, delay, capacity, and policy constraints.")}
  <section class="scenario-grid">${cards.map(c => `<article class="card scenario searchable ${c[6] ? "recommended" : ""}">${c[6] ? status("RECOMMENDED") : status("FEASIBLE")}<h2>${c[0]}</h2><p>${c[1]}</p><div class="facts"><div class="fact"><span>Cost</span><strong>${c[2]}</strong></div><div class="fact"><span>Delay</span><strong>${c[3]}</strong></div><div class="fact"><span>Protected</span><strong>${c[4]}</strong></div><div class="fact"><span>Feasibility</span><strong>${c[5]}</strong></div></div><div class="scenario-score"><span>Objective score</span><strong>${c[5]}</strong></div></article>`).join("")}</section>`;
}

function recommendations() {
  return `${pageHead("Decisioning", "Recommendation evidence", "The recommendation is grounded in deterministic calculations; AI is limited to the explanatory narrative.", `<button class="button" data-go="approvals">Open approval →</button>`)}
  <section class="grid-2"><article class="card panel searchable"><div class="card-heading"><div><p class="eyebrow">Recommended action</p><h2>Activate alternate source</h2><p>Shift 320 urgent CPU-X9 units to Hanseong Semiconductors.</p></div>${status("88% CONFIDENCE")}</div><p class="notice">This option protects the most revenue within the approved disruption budget while maintaining qualified-source and capacity constraints.</p><div class="facts"><div class="fact"><span>Revenue protected</span><strong>₹5.12 Cr</strong></div><div class="fact"><span>Incremental cost</span><strong>₹1.65 Cr</strong></div><div class="fact"><span>Orders protected</span><strong>15 of 18</strong></div></div></article><article class="card panel searchable"><div class="card-heading"><div><h2>Evidence and assumptions</h2><p>Auditable decision inputs</p></div>${status("VERSIONED")}</div><div class="timeline"><div class="timeline-item"><span class="timeline-dot"></span><span>Hanseong qualification remains valid</span><small>Assumption</small></div><div class="timeline-item"><span class="timeline-dot"></span><span>38% alternate weekly capacity available</span><small>Constraint</small></div><div class="timeline-item"><span class="timeline-dot"></span><span>₹2 Cr incident-response budget ceiling</span><small>Policy</small></div><div class="timeline-item"><span class="timeline-dot"></span><span>Maximize protected revenue</span><small>Objective</small></div></div></article></section>`;
}

function approvals() {
  return `${pageHead("Decisioning", "Approval center", "Govern high-impact recommendations with role-aware decisions and an immutable history.")}
  <section class="list"><article class="card list-card searchable"><div><span class="eyebrow">APR-2026-0915-01</span><h2>Activate alternate source for Taiwan disruption</h2><p>₹1.65 Cr incremental procurement and logistics commitment · Required role: APPROVER</p></div><div class="list-actions" id="approval-actions">${state.approval === "PENDING" ? `<button class="button secondary" data-approval="REJECTED">Reject</button><button class="button" data-approval="APPROVED">Approve</button>` : status(state.approval)}</div></article></section>
  <section class="grid-even"><article class="card panel"><div class="card-heading"><div><h2>Decision policy</h2><p>Approval routing snapshot</p></div>${status("ENFORCED")}</div><div class="code">IF incremental_cost &gt; ₹50 L\nTHEN require role APPROVER\nAND capture decision comment\nAND append audit event</div></article><article class="card panel"><div class="card-heading"><div><h2>Demonstration behavior</h2><p>Local browser-only interaction</p></div>${status("STATIC")}</div><p class="notice">Approve or reject to preview the interface. GitHub Pages cannot persist the decision; reload or use the reset control to restore the pending state.</p></article></section>`;
}

function executions() {
  const executionStatus = state.approval === "APPROVED" ? "SUCCEEDED" : "PENDING";
  return `${pageHead("Decisioning", "Execution status", "Observe idempotent adapter actions and external references after approval.")}
  <section class="list"><article class="card list-card searchable"><div><span class="eyebrow">SWITCH_SUPPLIER</span><h2>Create alternate-source purchase order</h2><p>Adapter: mock.erp@1.0 · Idempotency key: REC-0915-HANSEONG</p></div><div class="list-actions">${status(executionStatus)}</div></article><article class="card list-card searchable"><div><span class="eyebrow">EXPEDITE_SHIPMENT</span><h2>Reserve priority ocean capacity</h2><p>Adapter: mock.shipment@1.0 · Awaiting recommendation approval</p></div><div class="list-actions">${status("PENDING")}</div></article></section>`;
}

function workflows() {
  return `${pageHead("Control plane", "Workflow management", "Inspect the published, immutable disruption-response workflow and its ordered stages.", `<button class="button" data-go="simulations">Run simulation →</button>`)}
  <section class="card panel searchable"><div class="card-heading"><div><span class="eyebrow">disruption-response · version 1</span><h2>Canonical disruption response</h2><p>Published 15 September 2026 · changes require a cloned draft</p></div>${status("PUBLISHED")}</div><div class="stage-flow">${workflowStages.map((s, i) => `<div class="stage"><span>${i + 1}</span><strong>${s}</strong><small>deterministic handler</small></div>`).join("")}</div></section>
  <section class="grid-even"><article class="card panel"><div class="card-heading"><div><h2>Graph integrity</h2><p>Validated before publication</p></div>${status("VALID DAG")}</div><div class="facts"><div class="fact"><span>Stages</span><strong>8</strong></div><div class="fact"><span>Dependencies</span><strong>7</strong></div><div class="fact"><span>Cycles</span><strong>0</strong></div></div></article><article class="card panel"><div class="card-heading"><div><h2>Governance</h2><p>Control-plane safeguards</p></div>${status("RBAC")}</div><p class="notice">Draft mutations require administrator or supply-chain-manager roles. Publication, cloning, configuration, and simulation events are audit logged.</p></article></section>`;
}

function simulations() {
  const buttonLabel = state.simulation >= 0 && state.simulation < workflowStages.length ? "Simulation running…" : "Run Taiwan simulation";
  return `${pageHead("Control plane", "Simulation experience", "Preview stage-by-stage orchestration using the published workflow and Taiwan typhoon scenario.", `<button class="button" id="run-simulation" ${state.simulation >= 0 && state.simulation < workflowStages.length ? "disabled" : ""}>${buttonLabel}</button>`)}
  <section class="card panel"><div class="card-heading"><div><h2>Disruption response · version 1</h2><p>Incident: Taiwan Typhoon · Simulation does not execute external actions</p></div>${status(state.simulation === workflowStages.length ? "SUCCEEDED" : state.simulation >= 0 ? "RUNNING" : "READY")}</div><div class="stage-flow">${workflowStages.map((s, i) => { const klass = state.simulation < 0 || i > state.simulation ? "pending" : i === state.simulation && state.simulation < workflowStages.length ? "running" : ""; return `<div class="stage ${klass}"><span>${i + 1}</span><strong>${s}</strong><small>${klass === "running" ? "executing…" : klass === "pending" ? "pending" : "succeeded · 4 ms"}</small></div>`; }).join("")}</div></section>
  <section class="grid-even"><article class="card panel"><div class="card-heading"><div><h2>Simulation parameters</h2><p>Snapshot input</p></div>${status("NO SIDE EFFECTS")}</div><div class="code">incident: INC-2026-0915-01\ndelay_days: 7\navailable_capacity: 38%\nobjective: MAX_REVENUE_PROTECTED</div></article><article class="card panel"><div class="card-heading"><div><h2>Outcome</h2><p>Latest local demonstration result</p></div>${state.simulation === workflowStages.length ? status("SUCCEEDED") : status("AWAITING RUN")}</div><div class="facts"><div class="fact"><span>Selected</span><strong>${state.simulation === workflowStages.length ? "Alternate source" : "—"}</strong></div><div class="fact"><span>Protected</span><strong>${state.simulation === workflowStages.length ? "₹5.12 Cr" : "—"}</strong></div><div class="fact"><span>Stages</span><strong>${Math.max(0, Math.min(workflowStages.length, state.simulation + 1))}/8</strong></div></div></article></section>`;
}

function integrations() {
  const rows = [["Nova ERP", "ERP", "mock.erp@1.0", "MOCK MODE"], ["Global Weather", "WEATHER", "mock.weather@1.0", "MOCK MODE"], ["Trusted News", "NEWS", "mock.news@1.0", "MOCK MODE"], ["Ocean Tracking", "SHIPMENT", "mock.shipment@1.0", "MOCK MODE"], ["Supplier Feed", "SUPPLIER", "mock.supplier@1.0", "MOCK MODE"]];
  return `${pageHead("Settings", "Integrations", "Versioned connector configurations and current synchronization state.")}<section class="card table-wrap"><table><thead><tr><th>Integration</th><th>Type</th><th>Adapter</th><th>Status</th></tr></thead><tbody>${rows.map(r => `<tr class="searchable"><td><strong>${r[0]}</strong></td><td>${r[1]}</td><td><code>${r[2]}</code></td><td>${status(r[3])}</td></tr>`).join("")}</tbody></table></section><p class="notice" style="margin-top:16px">The GitHub Pages edition uses bundled demonstration data. Live provider credentials and synchronization require the containerized backend deployment.</p>`;
}

function audit() {
  const events = [["08:17:31", "recommendation.created", "REC-0915-01", "system"], ["08:17:32", "approval.requested", "APR-0915-01", "system"], ["08:16:58", "simulation.executed", "RUN-0915-07", "Aarav Mehta"], ["08:15:43", "workflow.published", "VERSION-1", "Aarav Mehta"], ["08:14:09", "incident.assessed", "INC-0915-01", "system"]];
  return `${pageHead("Governance", "Audit history", "Request-correlated evidence for workflow, approval, recommendation, simulation, and execution activity.")}<section class="card table-wrap"><table><thead><tr><th>Time</th><th>Action</th><th>Entity</th><th>Actor</th></tr></thead><tbody>${events.map(e => `<tr class="searchable"><td>${e[0]}</td><td><strong>${e[1]}</strong></td><td><code>${e[2]}</code></td><td>${e[3]}</td></tr>`).join("")}</tbody></table></section>`;
}

const screens = { "command-center": commandCenter, disruptions, "supply-network": supplyNetwork, suppliers: () => dataTablePage("suppliers"), inventory: () => dataTablePage("inventory"), shipments, scenarios, recommendations, approvals, executions, workflows, simulations, integrations, audit };

function renderNavigation() {
  document.querySelector("#navigation").innerHTML = navigationGroups.map(([group, links]) => `<div class="nav-group"><p class="nav-label">${group}</p>${links.map(([id, label, icon]) => `<button class="nav-link" data-go="${id}" title="${label}"><span class="nav-icon" aria-hidden="true">${icon}</span><span>${label}</span></button>`).join("")}</div>`).join("");
}

function currentScreen() {
  const id = location.hash.slice(1);
  return screens[id] ? id : "command-center";
}

function render() {
  const screen = currentScreen();
  document.querySelector("#content").innerHTML = screens[screen]();
  document.querySelectorAll(".nav-link").forEach(link => link.classList.toggle("active", link.dataset.go === screen));
  document.querySelector("#search").value = "";
  bindActions();
  document.title = `${navigationGroups.flatMap(g => g[1]).find(i => i[0] === screen)?.[1] || "Autopilot"} — Supply Chain Autopilot`;
  window.scrollTo({ top: 0, behavior: "instant" });
}

function toast(message) {
  const element = document.querySelector("#toast");
  element.textContent = message;
  element.classList.add("show");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => element.classList.remove("show"), 2600);
}

function bindActions() {
  document.querySelectorAll("#content [data-go]").forEach(button => button.addEventListener("click", () => { location.hash = button.dataset.go; }));
  document.querySelectorAll("[data-approval]").forEach(button => button.addEventListener("click", () => {
    state.approval = button.dataset.approval;
    toast(`Recommendation ${state.approval.toLowerCase()} in this demo.`);
    render();
  }));
  document.querySelector("#run-simulation")?.addEventListener("click", runSimulation);
}

function runSimulation() {
  clearInterval(state.simulationTimer);
  state.simulation = 0;
  render();
  state.simulationTimer = setInterval(() => {
    state.simulation += 1;
    render();
    if (state.simulation >= workflowStages.length) {
      clearInterval(state.simulationTimer);
      toast("Simulation completed: alternate source recommended.");
    }
  }, 420);
}

function filterScreen(query) {
  const term = query.trim().toLowerCase();
  const items = [...document.querySelectorAll(".searchable")];
  items.forEach(item => { item.hidden = term && !item.textContent.toLowerCase().includes(term); });
  let empty = document.querySelector("#filter-empty");
  if (term && items.length && items.every(item => item.hidden)) {
    if (!empty) {
      empty = document.createElement("div");
      empty.id = "filter-empty";
      empty.className = "card empty-filter";
      empty.textContent = `No visible records match “${query}”.`;
      document.querySelector("#content").append(empty);
    }
  } else {
    empty?.remove();
  }
}

renderNavigation();
document.querySelector("#navigation").addEventListener("click", event => {
  const button = event.target.closest("[data-go]");
  if (button) location.hash = button.dataset.go;
});
document.querySelector("#search").addEventListener("input", event => filterScreen(event.target.value));
document.querySelector("#reset-demo").addEventListener("click", () => {
  clearInterval(state.simulationTimer);
  Object.assign(state, { approval: "PENDING", execution: "PENDING", simulation: -1, simulationTimer: null });
  toast("Static demo state reset.");
  render();
});
window.addEventListener("hashchange", render);
if (!location.hash) history.replaceState(null, "", "#command-center");
render();

const state = {
  deals: [],
  portfolio: null,
  selectedDealId: null,
};

async function api(path, options = {}) {
  const response = await fetch(`/api${path}`, {
    ...options,
    headers: {
      "content-type": "application/json",
      ...(options.headers || {}),
    },
  });
  if (!response.ok) {
    throw new Error(`API ${response.status}`);
  }
  return response.json();
}

async function loadDeals() {
  const [deals, portfolio] = await Promise.all([api("/deals"), api("/portfolio/summary")]);
  state.deals = deals;
  state.portfolio = portfolio;
  if (!state.selectedDealId && state.deals.length > 0) {
    state.selectedDealId = state.deals[0].id;
  }
  render();
}

function render() {
  renderPortfolio();
  renderPipeline();
  renderDetail();
  renderDocuments();
  renderFinancialModel();
  renderMarketContext();
  renderAlerts();
}

function renderPortfolio() {
  const statuses = countBy(state.deals, (deal) => deal.status);
  const openAlerts = state.deals.flatMap((deal) => deal.alerts || []).filter((alert) => ["open", "escalated"].includes(alert.status));
  const summary = state.portfolio || {};
  document.querySelector("#portfolio").innerHTML = [
    metric("Deals", summary.deal_count ?? state.deals.length),
    metric("Portfolio value", formatCurrency(summary.current_portfolio_value)),
    metric("Equity invested", formatCurrency(summary.equity_invested)),
    metric("Unrealized gains", formatCurrency(summary.unrealized_gains)),
    metric("Open alerts", summary.open_alert_count ?? openAlerts.length),
    metric("Covenant watch", summary.covenant_watch_count ?? 0),
    metric("Sponsors", Object.keys(summary.exposure_by_sponsor || {}).length),
    metric("Capital calls", (summary.upcoming_capital_calls || []).length),
    metric("Rejected memory", statuses.rejected || 0),
  ].join("");
}

function renderPipeline() {
  const pipeline = document.querySelector("#pipeline");
  if (state.deals.length === 0) {
    pipeline.innerHTML = "<p>No deals yet.</p>";
    return;
  }
  const statuses = ["new", "screening", "underwriting", "investment_committee", "loi", "diligence", "acquired", "rejected", "watchlist"];
  pipeline.innerHTML = statuses
    .map((status) => {
      const deals = state.deals.filter((deal) => deal.status === status);
      return `
        <section class="pipeline-column">
          <h3>${escapeHtml(status.replaceAll("_", " "))}</h3>
          ${deals.length ? deals.map(dealCard).join("") : '<p class="empty-column">None</p>'}
        </section>
      `;
    })
    .join("");
  pipeline.querySelectorAll("[data-deal-id]").forEach((card) => {
    card.addEventListener("click", () => {
      state.selectedDealId = card.dataset.dealId;
      render();
    });
  });
}

function dealCard(deal) {
  const title = escapeHtml(deal.identity.name);
  const topAlert = (deal.alerts || []).find((alert) => ["critical", "high"].includes(alert.severity)) || (deal.alerts || [])[0];
  const price = assumptionValue(deal, ["purchase_price", "current_value", "asset_value"]);
  const irr = scenarioOutput(deal, "irr");
  const equityMultiple = scenarioOutput(deal, "equity_multiple");
  const updated = latestDealDate(deal);
  const meta = [deal.identity.asset_type, deal.identity.address].filter(Boolean).join(" | ");
  return `
    <article class="deal-card" data-deal-id="${deal.id}">
      <strong>${title}</strong>
      <small>${escapeHtml(meta || "No asset metadata")}</small>
      <dl>
        <div><dt>Price</dt><dd>${escapeHtml(formatValue(price) || "n/a")}</dd></div>
        <div><dt>IRR</dt><dd>${escapeHtml(formatValue(irr) || "n/a")}</dd></div>
        <div><dt>EM</dt><dd>${escapeHtml(formatValue(equityMultiple) || "n/a")}</dd></div>
        <div><dt>Owner</dt><dd>${escapeHtml(deal.identity.owner || "n/a")}</dd></div>
        <div><dt>Alerts</dt><dd>${(deal.alerts || []).length}</dd></div>
      </dl>
      <small>Top risk: ${escapeHtml(topAlert ? topAlert.title : "None")}</small>
      <small>Last update: ${escapeHtml(updated || "n/a")}</small>
    </article>
  `;
}

function renderDetail() {
  const deal = selectedDeal();
  const detail = document.querySelector("#deal-detail");
  if (!deal) {
    detail.innerHTML = "<p>Select or create a deal.</p>";
    document.querySelector("#memo").textContent = "";
    document.querySelector("#documents").innerHTML = "<p>Select or create a deal.</p>";
    document.querySelector("#financial-model").innerHTML = "<p>Select or create a deal.</p>";
    document.querySelector("#market-context").innerHTML = "<p>Select or create a deal.</p>";
    return;
  }
  detail.innerHTML = `
    <strong>${escapeHtml(deal.identity.name)}</strong><br>
    Status: ${escapeHtml(deal.status)}<br>
    Address: ${escapeHtml(deal.identity.address || "Not specified")}<br>
    Facts: ${(deal.extracted_facts || []).length}<br>
    Assumptions: ${(deal.assumptions || []).length}<br>
    Scenarios: ${(deal.scenarios || []).length}<br>
    Decision events: ${(deal.decision_history || []).length}
  `;
  renderMemo(deal);
}

function renderDocuments() {
  const deal = selectedDeal();
  const target = document.querySelector("#documents");
  if (!deal) {
    target.innerHTML = "<p>Select or create a deal.</p>";
    return;
  }
  const documents = deal.documents || [];
  const facts = deal.extracted_facts || [];
  if (documents.length === 0 && facts.length === 0) {
    target.innerHTML = "<p>No documents or extracted facts.</p>";
    return;
  }
  target.innerHTML = [
    ...documents.map((doc) => `<div class="review-item"><strong>${escapeHtml(doc.name)}</strong><small>${escapeHtml(doc.document_type)} | ${escapeHtml(doc.uploaded_by)} | ${escapeHtml(doc.storage_uri)}</small></div>`),
    ...facts.map((fact) => {
      const source = fact.source || {};
      const location = [source.name, source.page ? `page ${source.page}` : null, source.sheet, source.cell].filter(Boolean).join(" | ");
      return `<div class="review-item"><strong>${escapeHtml(fact.field_name)}: ${escapeHtml(formatValue(fact.value))}</strong><small>${escapeHtml(fact.status)} | confidence ${Math.round((fact.confidence || 0) * 100)}% | ${escapeHtml(location)}</small></div>`;
    }),
  ].join("");
}

function renderFinancialModel() {
  const deal = selectedDeal();
  const target = document.querySelector("#financial-model");
  if (!deal) {
    target.innerHTML = "<p>Select or create a deal.</p>";
    return;
  }
  const scenarios = deal.scenarios || [];
  const projected = deal.projected_cash_flows || [];
  const actual = deal.actual_cash_flows || [];
  const rentRoll = deal.rent_roll || [];
  if (scenarios.length === 0 && projected.length === 0 && actual.length === 0 && rentRoll.length === 0) {
    target.innerHTML = "<p>No scenarios, cash-flow records, or rent-roll rows.</p>";
    return;
  }
  target.innerHTML = [
    ...scenarios.map((scenario) => {
      const outputs = Object.entries(scenario.outputs || {}).map(([key, value]) => `${key}: ${formatValue(value)}`).join(" | ") || "No outputs";
      return `<div class="model-item"><strong>${escapeHtml(scenario.name)}</strong><small>${escapeHtml(scenario.scenario_type)} | ${escapeHtml(outputs)}</small></div>`;
    }),
    ...projected.map((row) => cashFlowRow("Projected", row)),
    ...actual.map((row) => cashFlowRow("Actual", row)),
    ...rentRoll.map((row) => rentRollRow(row)),
  ].join("");
}

function renderMarketContext() {
  const deal = selectedDeal();
  const target = document.querySelector("#market-context");
  if (!deal) {
    target.innerHTML = "<p>Select or create a deal.</p>";
    return;
  }
  const rows = [
    ...(deal.assets || []).map((asset) => marketItemHtml("Asset", asset.name, assetDetailHtml(asset))),
    ...(deal.market_comps || []).map((comp) => marketItem("Comp", comp.name, `${comp.comp_type} | ${formatValue(comp.value)}`)),
    ...(deal.property_records || []).map((record) => marketItem("Property", record.source, [record.parcel_id, record.zoning, record.flood_zone].filter(Boolean).join(" | "))),
    ...(deal.location_context || []).map((item) => marketItem("Location", item.name, [item.item_type, item.distance_miles && `${item.distance_miles} mi`, item.notes].filter(Boolean).join(" | "))),
    ...(deal.permit_events || []).map((permit) => marketItem("Permit", permit.permit_number, [permit.permit_type, permit.status, permit.issued_date].filter(Boolean).join(" | "))),
    ...(deal.news_events || []).map((event) => marketItem("News", event.title, event.classification)),
    ...(deal.imagery_snapshots || []).map((snapshot) => marketItem("Imagery", snapshot.source, `${snapshot.captured_at} | ${snapshot.storage_uri}`)),
    ...(deal.web_sources || []).map((source) => marketItem("Source", source.title, source.url)),
  ];
  target.innerHTML = rows.length > 0 ? rows.join("") : "<p>No market context yet.</p>";
}

function renderAlerts() {
  const alerts = state.deals.flatMap((deal) => (deal.alerts || []).map((alert) => ({ deal, alert })));
  const target = document.querySelector("#alerts");
  if (alerts.length === 0) {
    target.innerHTML = "<p>No alerts.</p>";
    return;
  }
  target.innerHTML = alerts
    .map(({ deal, alert }) => `<div class="alert-item"><strong>${escapeHtml(alert.title)}</strong><small>${escapeHtml(deal.identity.name)} | ${escapeHtml(alert.severity)} | ${escapeHtml(alert.status)}</small></div>`)
    .join("");
}

function cashFlowRow(label, row) {
  return `<div class="model-item"><strong>${escapeHtml(label)} ${escapeHtml(row.category)}</strong><small>${escapeHtml(row.period)} | ${escapeHtml(formatValue(row.amount))}</small></div>`;
}

function rentRollRow(row) {
  const detail = [
    row.as_of_date,
    row.tenant_name || (row.occupied ? "Occupied" : "Vacant"),
    `actual ${formatValue(row.monthly_rent)}`,
    row.market_rent ? `market ${formatValue(row.market_rent)}` : null,
  ].filter(Boolean).join(" | ");
  return `<div class="model-item"><strong>Rent Roll ${escapeHtml(row.unit)}</strong><small>${escapeHtml(detail)}</small></div>`;
}

function marketItem(label, title, detail) {
  return `<div class="context-item"><span>${escapeHtml(label)}</span><strong>${escapeHtml(title)}</strong><small>${escapeHtml(detail || "Not specified")}</small></div>`;
}

function marketItemHtml(label, title, detailHtml) {
  return `<div class="context-item"><span>${escapeHtml(label)}</span><strong>${escapeHtml(title)}</strong><small>${detailHtml || "Not specified"}</small></div>`;
}

function assetDetailHtml(asset) {
  const detail = [asset.asset_type, asset.address && asset.address.line1].filter(Boolean).join(" | ");
  if (!asset.coordinates) {
    return escapeHtml(detail);
  }
  const lat = formatValue(asset.coordinates.latitude);
  const lon = formatValue(asset.coordinates.longitude);
  const url = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(`${lat},${lon}`)}`;
  const label = detail ? `${detail} | Map ${lat}, ${lon}` : `Map ${lat}, ${lon}`;
  return `<a href="${escapeHtml(url)}" target="_blank" rel="noreferrer">${escapeHtml(label)}</a>`;
}

function renderMemo(deal) {
  const lines = [
    `# Investment Committee Memo: ${deal.identity.name}`,
    "",
    "## Deal Summary",
    `- Status: ${deal.status}`,
    `- Asset type: ${deal.identity.asset_type || "Not specified"}`,
    `- Address: ${deal.identity.address || "Not specified"}`,
    "",
    "## Alerts and Red Flags",
    ...(deal.alerts || []).map((alert) => `- ${alert.severity.toUpperCase()}: ${alert.title}`),
    "",
    "Human approval required before circulation.",
  ];
  document.querySelector("#memo").textContent = lines.join("\n");
}

function metric(label, value) {
  return `<div class="metric"><span>${escapeHtml(label)}</span><strong>${value}</strong></div>`;
}

function countBy(items, keyFn) {
  return items.reduce((counts, item) => {
    const key = keyFn(item);
    counts[key] = (counts[key] || 0) + 1;
    return counts;
  }, {});
}

function assumptionValue(deal, names) {
  const assumptions = deal.assumptions || [];
  const match = assumptions.find((assumption) => names.includes(assumption.name));
  return match ? match.value : null;
}

function scenarioOutput(deal, metric) {
  const scenarios = deal.scenarios || [];
  const preferred = scenarios.find((scenario) => scenario.outputs && scenario.outputs[metric] !== undefined);
  return preferred ? preferred.outputs[metric] : null;
}

function latestDealDate(deal) {
  const dates = [
    deal.received_at,
    ...(deal.decision_history || []).map((event) => event.occurred_at),
    ...(deal.alerts || []).map((alert) => alert.created_at),
  ].filter(Boolean).map(formatValue);
  return dates.sort().at(-1);
}

function selectedDeal() {
  return state.deals.find((deal) => deal.id === state.selectedDealId) || null;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  })[char]);
}

function formatValue(value) {
  if (value && typeof value === "object" && "value" in value) {
    return value.value;
  }
  return value ?? "";
}

function formatCurrency(value) {
  const normalized = Number(formatValue(value) || 0);
  if (!Number.isFinite(normalized)) {
    return formatValue(value);
  }
  return normalized.toLocaleString(undefined, { maximumFractionDigits: 0 });
}

document.querySelector("#refresh").addEventListener("click", loadDeals);
document.querySelector("#create-deal").addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(event.currentTarget);
  const payload = Object.fromEntries(formData.entries());
  const deal = await api("/deals", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  state.selectedDealId = deal.id;
  event.currentTarget.reset();
  await loadDeals();
});

loadDeals().catch((error) => {
  document.querySelector("#portfolio").innerHTML = `<p>${escapeHtml(error.message)}</p>`;
});

import React, { useEffect, useState } from "react";

type Deal = {
  id: string;
  status: string;
  identity: {
    name: string;
    address?: string;
    asset_type?: string;
    sponsor?: string;
  };
  alerts: Array<{ id: string; title: string; severity: string; status: string }>;
  extracted_facts: unknown[];
  assumptions: unknown[];
  scenarios: unknown[];
};

async function api<T>(path: string): Promise<T> {
  const response = await fetch(`/api${path}`);
  if (!response.ok) throw new Error(`API ${response.status}`);
  return response.json();
}

export function App() {
  const [deals, setDeals] = useState<Deal[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    api<Deal[]>("/deals").then((items) => {
      setDeals(items);
      setSelectedId((current) => current ?? items[0]?.id ?? null);
    });
  }, []);

  const selected = deals.find((deal) => deal.id === selectedId);
  const openAlerts = deals.flatMap((deal) => deal.alerts.filter((alert) => alert.status === "open"));

  return (
    <main className="shell">
      <aside className="sidebar">
        <h1>Real Estate Helm</h1>
        <button>Portfolio</button>
        <button>Pipeline</button>
        <button>Monitoring</button>
        <button>IC Memo</button>
      </aside>
      <section className="workspace">
        <header className="dashboard">
          <Metric label="Deals" value={deals.length} />
          <Metric label="Open alerts" value={openAlerts.length} />
          <Metric label="Rejected memory" value={deals.filter((deal) => deal.status === "rejected").length} />
        </header>
        <section className="grid">
          <div className="panel">
            <h2>Deal Pipeline</h2>
            {deals.map((deal) => (
              <button className="deal-row" key={deal.id} onClick={() => setSelectedId(deal.id)}>
                <strong>{deal.identity.name}</strong>
                <span>{[deal.status, deal.identity.asset_type, deal.identity.address].filter(Boolean).join(" | ")}</span>
              </button>
            ))}
          </div>
          <div className="panel">
            <h2>Deal Detail</h2>
            {selected ? (
              <dl>
                <dt>Status</dt>
                <dd>{selected.status}</dd>
                <dt>Facts</dt>
                <dd>{selected.extracted_facts.length}</dd>
                <dt>Assumptions</dt>
                <dd>{selected.assumptions.length}</dd>
                <dt>Scenarios</dt>
                <dd>{selected.scenarios.length}</dd>
              </dl>
            ) : (
              <p>No deal selected.</p>
            )}
          </div>
          <div className="panel">
            <h2>Monitoring Center</h2>
            {openAlerts.map((alert) => (
              <article className="alert" key={alert.id}>
                <strong>{alert.title}</strong>
                <span>{alert.severity}</span>
              </article>
            ))}
          </div>
        </section>
      </section>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

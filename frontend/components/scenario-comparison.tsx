"use client";

import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { Scenario } from "../lib/api";
import { StatusPill } from "./status-pill";

export function ScenarioComparison({ scenarios }: { scenarios: Scenario[] }) {
  const data = scenarios.map((scenario) => ({
    name: scenario.name,
    cost: Number(scenario.incremental_cost),
    protected: Number(scenario.revenue_protected),
    delay: Number(scenario.delay_days),
  }));
  if (!scenarios.length) return null;
  return <>
    <section className="card panel chart-panel" aria-label="Scenario cost and protected revenue comparison">
      <ResponsiveContainer width="100%" height={310}>
        <BarChart data={data} margin={{ left: 12, right: 12 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="name" tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip formatter={(value) => new Intl.NumberFormat("en-IN").format(Number(value))} />
          <Legend />
          <Bar dataKey="protected" name="Revenue protected" fill="#176a45" radius={[6, 6, 0, 0]} />
          <Bar dataKey="cost" name="Incremental cost" fill="#d7a94a" radius={[6, 6, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </section>
    <section className="comparison-grid">
      {scenarios.map((scenario) => <article className="card scenario-card" key={scenario.id}>
        <div className="card-heading"><h2>{scenario.name}</h2><StatusPill value={scenario.status} /></div>
        <dl className="fact-grid">
          <div><dt>Revenue protected</dt><dd>₹{Number(scenario.revenue_protected).toLocaleString("en-IN")}</dd></div>
          <div><dt>Incremental cost</dt><dd>₹{Number(scenario.incremental_cost).toLocaleString("en-IN")}</dd></div>
          <div><dt>Expected delay</dt><dd>{scenario.delay_days} days</dd></div>
          <div><dt>Feasibility</dt><dd>{Math.round(Number(scenario.feasibility_score) * 100)}%</dd></div>
        </dl>
        <details><summary>Assumptions and constraints</summary><pre>{JSON.stringify({ assumptions: scenario.assumptions, constraints: scenario.constraints }, null, 2)}</pre></details>
      </article>)}
    </section>
  </>;
}

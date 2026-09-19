import { Activity, ArrowUpRight, CircleCheck, ShieldAlert } from "lucide-react";

import { DataUnavailable } from "../components/data-unavailable";
import { PageHeader } from "../components/page-header";
import { getHealth, getOverview } from "../lib/api";

export const dynamic = "force-dynamic";

export default async function CommandCenter() {
  const health = await getHealth();
  const overview = await getOverview();
  const connected = health?.status === "healthy";
  return <>
    <PageHeader eyebrow="Command center" title="Operate ahead of disruption." description="A connected workspace for signals, deterministic impact analysis, mitigation choices, and governed action." />
    <section className="metrics" aria-label="Operational summary">
      <article className="card metric"><div className="metric-label">API status</div><div className="metric-value"><span className={`status ${connected ? "healthy" : "unavailable"}`}>{connected ? "Connected" : "Offline"}</span></div><div className="metric-detail">Live health endpoint: {connected ? "responding" : "not reachable"}.</div></article>
      <article className="card metric"><div className="metric-label">Active incidents</div><div className="metric-value">{overview?.active_incidents ?? "—"}</div><div className="metric-detail">Current non-resolved incidents in the tenant workspace.</div></article>
      <article className="card metric"><div className="metric-label">Revenue at risk</div><div className="metric-value">{overview ? `₹${overview.revenue_at_risk}` : "—"}</div><div className="metric-detail">Derived exclusively from persisted impact assessments.</div></article>
      <article className="card metric"><div className="metric-label">Open customer orders</div><div className="metric-value">{overview?.orders ?? "—"}</div><div className="metric-detail">Tenant-scoped customer order count.</div></article>
    </section>
    <section className="dashboard-grid">
      <article className="card panel"><div className="screen-toolbar"><div><h2>Decision readiness</h2><p>Connected to the tenant-scoped dashboard aggregation endpoint.</p></div><Activity color="var(--primary)" /></div>{overview ? <p>{overview.suppliers} suppliers and {overview.orders} customer orders are available for operational analysis.</p> : <DataUnavailable title="Decision data is unavailable" description="The frontend deliberately does not substitute placeholder business values when the backend cannot be reached." />}</article>
      <article className="card panel"><h2>Platform health</h2><p><CircleCheck size={16} color="var(--primary)" /> Backend foundation is {connected ? "available" : "unavailable"}.</p><p><ShieldAlert size={16} color="var(--high)" /> Operational APIs will be exposed with tenant-aware authentication before data becomes visible here.</p><a className="button" href="/disruptions">Open disruptions <ArrowUpRight size={15} /></a></article>
    </section>
  </>;
}

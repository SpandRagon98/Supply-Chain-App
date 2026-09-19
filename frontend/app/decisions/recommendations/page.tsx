import { DataUnavailable } from "../../../components/data-unavailable";
import { PageHeader } from "../../../components/page-header";
import { StatusPill } from "../../../components/status-pill";
import { getResource, type DecisionData } from "../../../lib/api";

export default async function RecommendationsPage() {
  const decisions = await getResource<DecisionData>("/decisions");
  return <><PageHeader eyebrow="Decision workspace" title="Recommendations" description="Review the selected scenario, deterministic evidence, confidence, assumptions, risks, and alternative path." />
    {decisions?.recommendations.length ? <section className="stack">{decisions.recommendations.map((item) => <article className="card recommendation-card" key={item.id}>
      <div className="card-heading"><div><span className="muted-label">Recommended scenario</span><h2>{item.scenario_name}</h2></div><StatusPill value={`${Math.round(Number(item.confidence) * 100)}% CONFIDENCE`} /></div>
      <p className="lead">{item.rationale ?? "A deterministic recommendation was produced from the configured objective."}</p>
      <div className="split-panel"><div><h3>Evidence summary</h3><pre>{JSON.stringify(item.structured_summary, null, 2)}</pre></div><div><h3>Assumptions and risks</h3><pre>{JSON.stringify({ assumptions: item.assumptions, risks: item.risks }, null, 2)}</pre></div></div>
    </article>)}</section> : <DataUnavailable title="No recommendation has been issued" description="Recommendations are created only after feasible scenarios have been evaluated by the configured deterministic objective." />}
  </>;
}

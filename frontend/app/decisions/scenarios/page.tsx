import { DataUnavailable } from "../../../components/data-unavailable";
import { PageHeader } from "../../../components/page-header";
import { ScenarioComparison } from "../../../components/scenario-comparison";
import { getResource, type DecisionData } from "../../../lib/api";

export default async function ScenarioComparisonPage() {
  const decisions = await getResource<DecisionData>("/decisions");
  return <><PageHeader eyebrow="Decision workspace" title="Scenario comparison" description="Compare quantified mitigation choices without hiding cost, delay, feasibility, assumptions, or constraints." />
    {decisions?.scenarios.length ? <ScenarioComparison scenarios={decisions.scenarios} /> : <DataUnavailable title="No scenarios are ready for comparison" description="Scenario candidates appear here after an incident has completed deterministic impact and risk assessment." />}
  </>;
}

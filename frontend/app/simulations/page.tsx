import { PageHeader } from "../../components/page-header";
import { SimulationRunner } from "../../components/simulation-runner";
import { getCollection, type Simulation, type Workflow } from "../../lib/api";

export default async function SimulationsPage() {
  const [workflows, runs] = await Promise.all([getCollection<Workflow>("/workflows"), getCollection<Simulation>("/simulations")]);
  return <><PageHeader eyebrow="Safe experimentation" title="Workflow simulation" description="Execute a published workflow with hypothetical disruption parameters and inspect persisted stage-by-stage progression." /><SimulationRunner workflows={workflows ?? []} initialRuns={runs ?? []} /></>;
}

import { ArrowUpRight } from "lucide-react";

import { DataUnavailable } from "../../components/data-unavailable";
import { PageHeader } from "../../components/page-header";
import { StatusPill } from "../../components/status-pill";
import { getCollection, type Workflow } from "../../lib/api";

export default async function WorkflowsPage() {
  const workflows = await getCollection<Workflow>("/workflows");
  return <><PageHeader eyebrow="Control plane" title="Workflow management" description="Inspect version history, clone immutable releases, validate drafts, and publish governed response flows." />
    {workflows?.length ? <section className="workflow-list">{workflows.map((workflow) => <article className="card workflow-card" key={workflow.id}><div><span className="muted-label">{workflow.key}</span><h2>{workflow.name}</h2><p>{workflow.description}</p></div><div className="version-list">{workflow.versions.map((version) => <a href={`/workflows/${version.id}`} key={version.id}><span>Version {version.version}</span><StatusPill value={version.status} /><ArrowUpRight size={15} /></a>)}</div></article>)}</section> : <DataUnavailable title="No workflows are configured" description="Create a workflow through the control-plane API, then add versioned stages and publish a validated graph." />}
  </>;
}

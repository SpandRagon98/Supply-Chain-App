import { DataUnavailable } from "../../components/data-unavailable";
import { PageHeader } from "../../components/page-header";
import { StatusPill } from "../../components/status-pill";
import { getCollection, type Execution } from "../../lib/api";

export default async function ExecutionsPage() {
  const executions = await getCollection<Execution>("/executions");
  return <><PageHeader eyebrow="Governed action" title="Execution status" description="Track idempotent mitigation commands, adapter attempts, external references, and recoverable failures." />
    {executions?.length ? <section className="stack">{executions.map((item) => <article className="card execution-row" key={item.id}><div><span className="muted-label">{item.adapter}</span><h2>{item.action_type.replaceAll("_", " ")}</h2><p>{item.external_reference ? `External reference ${item.external_reference}` : "Awaiting external reference"} · {item.attempt_count} attempt(s)</p></div><StatusPill value={item.status} />{item.error && <p className="error-text">{item.error}</p>}</article>)}</section> : <DataUnavailable title="No execution actions have been dispatched" description="Approved recommendations appear here as idempotent external-system commands with retry and result history." />}
  </>;
}

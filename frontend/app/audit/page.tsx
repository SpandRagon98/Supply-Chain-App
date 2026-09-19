import { DataUnavailable } from "../../components/data-unavailable";
import { PageHeader } from "../../components/page-header";
import { SettingsNav } from "../../components/settings-nav";
import { getCollection, type AuditEntry } from "../../lib/api";

export default async function AuditPage() {
  const entries = await getCollection<AuditEntry>("/audit-logs");
  return <><PageHeader eyebrow="Governance" title="Audit explorer" description="Trace actor, request, entity, workflow, and before/after state for governed product mutations." /><SettingsNav />
    {entries?.length ? <section className="audit-list">{entries.map((item) => <article className="card audit-entry" key={item.id}><time>{new Date(item.occurred_at).toLocaleString()}</time><div><strong>{item.action}</strong><span>{item.entity_type} {item.entity_id?.slice(0, 8)}</span></div><code>{item.request_id ?? "no request id"}</code><details><summary>State change</summary><pre>{JSON.stringify({ before: item.before, after: item.after, metadata: item.metadata }, null, 2)}</pre></details></article>)}</section> : <DataUnavailable title="No audit events have been recorded" description="Approval and control-plane mutations emit tenant-scoped audit records with request correlation." />}
  </>;
}

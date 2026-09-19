import { ArrowUpRight, Plus } from "lucide-react";

import { DataUnavailable } from "../../components/data-unavailable";
import { PageHeader } from "../../components/page-header";
import { RecordList } from "../../components/record-list";
import { getCollection, type Incident } from "../../lib/api";

export default async function DisruptionsPage() {
  const incidents = await getCollection<Incident>("/incidents");
  return <>
    <div className="screen-toolbar"><PageHeader eyebrow="Operational response" title="Disruptions" description="Investigate incoming signals, review incident confidence, and move deterministic decisions into governed action." /><button className="button"><Plus size={16} /> Add disruption</button></div>
    {incidents ? <RecordList columns={[{ key: "incident_number", label: "Incident" }, { key: "title", label: "Title" }, { key: "severity", label: "Severity" }, { key: "confidence", label: "Confidence" }, { key: "status", label: "Status" }]} rows={incidents} /> : <DataUnavailable title="No incident feed is connected yet" description="The backend has signal intelligence and an end-to-end Taiwan Typhoon validation. This screen will recover as soon as the API and tenant data are reachable." />}
    <section className="dashboard-grid"><article className="card panel"><h2>Incident details</h2><p>Each row will expose severity, confidence, affected suppliers, material propagation, revenue exposure, recommendation, and approvals.</p><a className="button" href="/supply-network">View supply network <ArrowUpRight size={15} /></a></article><article className="card panel"><h2>Human review is intentional</h2><p>Low-confidence entity matches remain review-gated. The interface will not promote a signal to a business decision without its deterministic evidence trail.</p></article></section>
  </>;
}

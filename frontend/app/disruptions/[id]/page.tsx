import { notFound } from "next/navigation";

import { DataUnavailable } from "../../../components/data-unavailable";
import { PageHeader } from "../../../components/page-header";
import { getResource } from "../../../lib/api";

export default async function DisruptionDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  if (!id.trim()) notFound();
  const detail = await getResource<Record<string, unknown>>(`/incidents/${id}`);
  return <><PageHeader eyebrow="Incident workspace" title={detail ? String((detail.incident as { title?: string }).title ?? id) : `Disruption ${id}`} description="A single explainable path from source signals through impact, risk, scenario choice, human approval, execution, and outcome." />{detail ? <section className="card panel"><h2>Lineaged decision record</h2><p>Risk, impact, and scenario data returned by the tenant API are available for this incident.</p><pre style={{ overflowX: "auto", padding: 16, borderRadius: 10, background: "var(--surface-muted)", fontSize: 12 }}>{JSON.stringify(detail, null, 2)}</pre></section> : <DataUnavailable title="Incident detail data is not available" description="This route uses the authenticated incident-detail API and shows only persisted, lineaged values and approval/execution history." />}</>;
}

import { DataUnavailable } from "../../../components/data-unavailable";
import { PageHeader } from "../../../components/page-header";
import { SettingsNav } from "../../../components/settings-nav";
import { StatusPill } from "../../../components/status-pill";
import { getResource, type SettingsData } from "../../../lib/api";

export default async function IntegrationsPage() {
  const settings = await getResource<SettingsData>("/settings");
  return <><PageHeader eyebrow="Settings" title="Integrations" description="Review ERP, weather, news, shipment, and supplier adapters without exposing secret material." /><SettingsNav />
    {settings?.integrations.length ? <section className="settings-grid">{settings.integrations.map((item) => <article className="card setting-card" key={item.id}><div className="card-heading"><div><span className="muted-label">{item.type}</span><h2>{item.name}</h2></div><StatusPill value={item.status} /></div><dl className="compact-facts"><div><dt>Adapter</dt><dd>{item.adapter}</dd></div><div><dt>Last sync</dt><dd>{item.last_sync_at ? new Date(item.last_sync_at).toLocaleString() : "Not run"}</dd></div></dl>{item.last_error && <p className="error-text">{item.last_error}</p>}</article>)}</section> : <DataUnavailable title="No integrations are configured" description="Connector configurations and health will appear here after tenant setup." />}
  </>;
}

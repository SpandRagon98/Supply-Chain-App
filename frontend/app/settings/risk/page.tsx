import { PageHeader } from "../../../components/page-header";
import { SettingsNav } from "../../../components/settings-nav";
import { getResource, type SettingsData } from "../../../lib/api";

export default async function RiskSettingsPage() {
  const settings = await getResource<SettingsData>("/settings");
  return <><PageHeader eyebrow="Settings" title="Risk & optimization" description="Inspect deterministic scoring weights, risk bands, and optimization objectives applied by the backend engines." /><SettingsNav />
    <section className="split-panel"><article className="card setting-card"><h2>Risk scoring</h2><p>Weights and thresholds are explicit and traceable for every assessment.</p><pre>{JSON.stringify(settings?.risk ?? {}, null, 2)}</pre></article><article className="card setting-card"><h2>Optimization</h2><p>The selected objective ranks feasible scenario outcomes without AI arithmetic.</p><pre>{JSON.stringify(settings?.optimization ?? {}, null, 2)}</pre></article></section>
  </>;
}

import { DataUnavailable } from "../../../components/data-unavailable";
import { PageHeader } from "../../../components/page-header";
import { SettingsNav } from "../../../components/settings-nav";
import { StatusPill } from "../../../components/status-pill";
import { getResource, type SettingsData } from "../../../lib/api";

export default async function AiSettingsPage() {
  const settings = await getResource<SettingsData>("/settings");
  return <><PageHeader eyebrow="Settings" title="AI configuration" description="Manage model routing and versioned prompts used only for explanations, extraction, and summaries—not numeric business truth." /><SettingsNav />
    {settings?.ai_models.length ? <section className="settings-grid">{settings.ai_models.map((item) => <article className="card setting-card" key={item.id}><div className="card-heading"><div><span className="muted-label">{item.provider}</span><h2>{item.model}</h2></div><StatusPill value={item.is_enabled ? "ENABLED" : "DISABLED"} /></div><p>{item.key}</p><pre>{JSON.stringify(item.parameters, null, 2)}</pre><small>Secret reference: {item.secret_reference ?? "No external secret required"}</small></article>)}{settings.prompt_templates.map((item) => <article className="card setting-card" key={item.id}><div className="card-heading"><div><span className="muted-label">Prompt v{item.version}</span><h2>{item.key}</h2></div><StatusPill value={item.status} /></div><p>{item.purpose}</p></article>)}</section> : <DataUnavailable title="No AI model configuration exists" description="The deterministic application remains usable without an AI provider; configured explanation models appear here." />}
  </>;
}

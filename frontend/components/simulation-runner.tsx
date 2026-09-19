"use client";

import { useState } from "react";
import { Play } from "lucide-react";

import type { Simulation, Workflow } from "../lib/api";
import { StatusPill } from "./status-pill";

export function SimulationRunner({ workflows, initialRuns }: { workflows: Workflow[]; initialRuns: Simulation[] }) {
  const published = workflows.flatMap((workflow) => workflow.versions.filter((version) => version.status === "PUBLISHED").map((version) => ({ id: version.id, label: `${workflow.name} v${version.version}` })));
  const [versionId, setVersionId] = useState(published[0]?.id ?? "");
  const [runs, setRuns] = useState(initialRuns);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [liveStages, setLiveStages] = useState<Simulation["stages"]>([]);

  async function run() {
    setBusy(true);
    setLiveStages([]);
    setMessage("Executing the published workflow through the backend engine…");
    const response = await fetch("/api/backend/simulations/stream", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ workflow_version_id: versionId, parameters: { demand_multiplier: 1.25, supplier_delay_days: 9 } }) });
    if (!response.ok || !response.body) {
      const body = await response.json().catch(() => null);
      setMessage(body?.error?.message ?? "Simulation failed.");
      setBusy(false);
      return;
    }
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { done, value } = await reader.read();
      buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";
      for (const line of lines.filter(Boolean)) {
        const event = JSON.parse(line) as { type: string; message?: string; id?: string; name?: string; status?: string; attempts?: number; duration_ms?: number | null };
        if (event.type === "stage") {
          setLiveStages((items) => [...items, { id: event.id ?? crypto.randomUUID(), name: event.name ?? "Stage", status: event.status ?? "SUCCEEDED", attempts: event.attempts ?? 1, duration_ms: event.duration_ms ?? null, output: {} }]);
        }
        if (event.type === "error") setMessage(event.message ?? "Simulation failed.");
      }
      if (done) break;
    }
    const refreshed = await fetch("/api/backend/simulations", { cache: "no-store" });
    const body = await refreshed.json();
    setRuns(body.data ?? []);
    setMessage("Simulation completed with persisted stage lineage.");
    setBusy(false);
  }

  return <div className="stack">
    <section className="card simulation-controls">
      <label><span className="field-label">Published workflow</span><select value={versionId} onChange={(event) => setVersionId(event.target.value)}>{published.map((version) => <option key={version.id} value={version.id}>{version.label}</option>)}</select></label>
      <button className="button" onClick={run} disabled={busy || !versionId}><Play size={15} /> {busy ? "Running…" : "Run simulation"}</button>
      {message && <p className="notice" role="status">{message}</p>}
    </section>
    {(busy || liveStages.length > 0) && <article className="card simulation-run" aria-live="polite"><div className="card-heading"><div><span className="muted-label">Live engine events</span><h2>Stage progression</h2></div><StatusPill value={busy ? "RUNNING" : "SUCCEEDED"} /></div><div className="stage-progress">{liveStages.map((stage, index) => <div className="stage-step" key={stage.id}><span>{index + 1}</span><div><strong>{stage.name}</strong><small>{stage.status} · {stage.duration_ms ?? 0} ms</small></div></div>)}</div></article>}
    {runs.map((run) => <article className="card simulation-run" key={run.id}>
      <div className="card-heading"><div><span className="muted-label">Run {run.id.slice(0, 8)}</span><h2>Workflow simulation</h2></div><StatusPill value={run.status} /></div>
      <div className="stage-progress">{run.stages.map((stage, index) => <div className="stage-step" key={stage.id}><span>{index + 1}</span><div><strong>{stage.name}</strong><small>{stage.status} · {stage.duration_ms ?? 0} ms</small></div></div>)}</div>
    </article>)}
  </div>;
}

"use client";

import "@xyflow/react/dist/style.css";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Background, Controls, MarkerType, MiniMap, ReactFlow, type Connection, type Edge, type Node } from "@xyflow/react";
import { Copy, Save, Send, ShieldCheck } from "lucide-react";

import type { WorkflowDetail, WorkflowStage } from "../lib/api";
import { StatusPill } from "./status-pill";

async function mutate(path: string, method = "POST", body?: unknown) {
  const response = await fetch(`/api/backend${path}`, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const payload = await response.json().catch(() => null);
  if (!response.ok) throw new Error(payload?.error?.message ?? "Workflow update failed");
  return payload.data;
}

export function WorkflowBuilder({ detail }: { detail: WorkflowDetail }) {
  const router = useRouter();
  const [selectedId, setSelectedId] = useState(detail.stages[0]?.id ?? null);
  const [draftConfig, setDraftConfig] = useState(JSON.stringify(detail.stages[0]?.configuration ?? {}, null, 2));
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const editable = detail.version.status === "DRAFT";
  const selected = detail.stages.find((stage) => stage.id === selectedId) ?? null;

  const nodes = useMemo<Node[]>(() => detail.stages.map((stage) => ({
    id: stage.id,
    position: { x: stage.position % 4 * 250, y: Math.floor(stage.position / 4) * 170 },
    data: { label: `${stage.position + 1}. ${stage.name}${stage.is_enabled ? "" : " (disabled)"}` },
    className: `workflow-node${stage.is_enabled ? "" : " disabled"}`,
  })), [detail.stages]);
  const edges = useMemo<Edge[]>(() => detail.dependencies.map((dependency) => ({
    id: dependency.id,
    source: dependency.depends_on_stage_id,
    target: dependency.stage_id,
    markerEnd: { type: MarkerType.ArrowClosed },
  })), [detail.dependencies]);

  function choose(stage: WorkflowStage) {
    setSelectedId(stage.id);
    setDraftConfig(JSON.stringify(stage.configuration, null, 2));
  }

  async function perform(action: () => Promise<unknown>, success: string) {
    setBusy(true);
    setMessage(null);
    try {
      await action();
      setMessage(success);
      router.refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Workflow update failed");
    } finally {
      setBusy(false);
    }
  }

  async function onConnect(connection: Connection) {
    if (!editable || !connection.source || !connection.target) return;
    await perform(
      () => mutate(`/workflow-versions/${detail.version.id}/dependencies`, "POST", { stage_id: connection.target, depends_on_stage_id: connection.source }),
      "Dependency added.",
    );
  }

  return <>
    <div className="builder-toolbar card">
      <div><strong>{detail.definition.name}</strong><span>Version {detail.version.version}</span><StatusPill value={detail.version.status} /></div>
      <div className="row-actions">
        <button className="button secondary" disabled={busy} onClick={() => perform(() => mutate(`/workflow-versions/${detail.version.id}/validate`), "Workflow graph is valid.")}><ShieldCheck size={15} /> Validate</button>
        {editable ? <button className="button" disabled={busy} onClick={() => perform(() => mutate(`/workflow-versions/${detail.version.id}/publish`), "Workflow published and locked.")}><Send size={15} /> Publish</button> : <button className="button" disabled={busy} onClick={() => perform(async () => {
          const version = await mutate(`/workflow-versions/${detail.version.id}/clone`) as { id: string };
          router.push(`/workflows/${version.id}`);
        }, "Draft version created.")}><Copy size={15} /> Clone to draft</button>}
      </div>
    </div>
    {message && <p className="notice" role="status">{message}</p>}
    <div className="workflow-layout">
      <section className="card workflow-canvas" aria-label="Visual workflow graph">
        <ReactFlow nodes={nodes} edges={edges} fitView onConnect={onConnect} nodesDraggable={false} onNodeClick={(_, node) => {
          const stage = detail.stages.find((item) => item.id === node.id);
          if (stage) choose(stage);
        }}>
          <Background /><MiniMap /><Controls />
        </ReactFlow>
      </section>
      <aside className="card config-drawer">
        {selected ? <>
          <div className="card-heading"><div><span className="muted-label">{selected.stage_type}</span><h2>{selected.name}</h2></div><StatusPill value={selected.is_enabled ? "ENABLED" : "DISABLED"} /></div>
          <p>{selected.description}</p>
          <label className="toggle"><input type="checkbox" checked={selected.is_enabled} disabled={!editable || busy} onChange={(event) => perform(() => mutate(`/workflow-stages/${selected.id}/enabled`, "PATCH", { enabled: event.target.checked }), "Stage state updated.")} /> Enabled in this version</label>
          <label className="field-label" htmlFor="stage-config">Configuration JSON</label>
          <textarea id="stage-config" value={draftConfig} disabled={!editable} onChange={(event) => setDraftConfig(event.target.value)} rows={12} />
          <button className="button" disabled={!editable || busy} onClick={() => perform(() => mutate(`/workflow-stages/${selected.id}/configuration`, "PATCH", { configuration: JSON.parse(draftConfig), retry_policy: selected.retry_policy, timeout_seconds: selected.timeout_seconds, failure_policy: selected.failure_policy }), "Stage configuration saved.")}><Save size={15} /> Save configuration</button>
          {!editable && <p className="helper">Published versions are immutable. Clone this version before editing.</p>}
        </> : <p>Select a stage to configure it.</p>}
      </aside>
    </div>
  </>;
}

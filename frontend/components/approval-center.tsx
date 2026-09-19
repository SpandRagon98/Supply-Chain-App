"use client";

import { useState } from "react";
import { Check, X } from "lucide-react";

import type { Approval } from "../lib/api";
import { StatusPill } from "./status-pill";

export function ApprovalCenter({ initialApprovals }: { initialApprovals: Approval[] }) {
  const [approvals, setApprovals] = useState(initialApprovals);
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function decide(id: string, decision: "APPROVED" | "REJECTED") {
    setBusy(id);
    setMessage(null);
    const response = await fetch(`/api/backend/approvals/${id}/decision`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision, comment: "Decision recorded in Approval Center" }),
    });
    if (response.ok) {
      setApprovals((items) => items.map((item) => item.id === id ? { ...item, status: decision } : item));
      setMessage(`Approval ${decision.toLowerCase()} and audit event recorded.`);
    } else {
      const body = await response.json().catch(() => null);
      setMessage(body?.error?.message ?? "The decision could not be recorded.");
    }
    setBusy(null);
  }

  return <div className="stack">
    {message && <p className="notice" role="status">{message}</p>}
    {approvals.map((approval) => <article className="card approval-row" key={approval.id}>
      <div><span className="muted-label">{approval.required_role.replaceAll("_", " ")}</span><h2>{approval.currency} {Number(approval.amount).toLocaleString("en-IN")}</h2><p>Recommendation {approval.recommendation_id.slice(0, 8)} · policy-routed request</p></div>
      <StatusPill value={approval.status} />
      {approval.status === "PENDING" && <div className="row-actions">
        <button className="button" disabled={busy === approval.id} onClick={() => decide(approval.id, "APPROVED")}><Check size={15} /> Approve</button>
        <button className="button secondary" disabled={busy === approval.id} onClick={() => decide(approval.id, "REJECTED")}><X size={15} /> Reject</button>
      </div>}
    </article>)}
  </div>;
}

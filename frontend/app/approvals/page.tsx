import { ApprovalCenter } from "../../components/approval-center";
import { DataUnavailable } from "../../components/data-unavailable";
import { PageHeader } from "../../components/page-header";
import { getCollection, type Approval } from "../../lib/api";

export default async function ApprovalsPage() {
  const approvals = await getCollection<Approval>("/approvals");
  return <><PageHeader eyebrow="Governed action" title="Approval center" description="Review policy-routed recommendations and record immutable approve or reject decisions with actor and request lineage." />
    {approvals?.length ? <ApprovalCenter initialApprovals={approvals} /> : <DataUnavailable title="No approval requests are pending" description="Requests appear when a recommendation crosses the configured amount or supplier policy threshold." />}
  </>;
}

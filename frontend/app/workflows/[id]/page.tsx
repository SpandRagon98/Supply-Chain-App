import { notFound } from "next/navigation";

import { PageHeader } from "../../../components/page-header";
import { WorkflowBuilder } from "../../../components/workflow-builder";
import { getResource, type WorkflowDetail } from "../../../lib/api";

export default async function WorkflowBuilderPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  if (!id.trim()) notFound();
  const detail = await getResource<WorkflowDetail>(`/workflow-versions/${id}`);
  if (!detail) notFound();
  return <><PageHeader eyebrow="Visual workflow builder" title={detail.definition.name} description="Select stages to configure them, connect nodes to add dependencies, validate the DAG, and publish an immutable version." /><WorkflowBuilder detail={detail} /></>;
}

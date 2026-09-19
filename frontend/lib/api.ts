export type HealthPayload = { status: "healthy" | "unhealthy"; checks: Record<string, { status: string }> };
type Envelope<T> = { data: T; meta: { request_id: string } };
export type Overview = { active_incidents: number; suppliers: number; orders: number; revenue_at_risk: string };
export type Incident = { id: string; incident_number: string; title: string; severity: string; confidence: string; status: string; started_at: string };
export type Supplier = { id: string; code: string; name: string; country_code: string; criticality: number; status: string };
export type Inventory = { id: string; facility_id: string; material_id: string | null; on_hand_quantity: string; allocated_quantity: string; unit_of_measure: string };
export type Shipment = { id: string; shipment_number: string; status: string; carrier: string | null; transportation_mode: string; estimated_arrival_at: string | null };
export type Scenario = { id: string; incident_id: string; name: string; status: string; incremental_cost: string; delay_days: string; revenue_protected: string; orders_protected: number; feasibility_score: string; objective_score: string | null; assumptions: Record<string, unknown>[]; constraints: Record<string, unknown>[]; actions: Record<string, unknown>[] };
export type Recommendation = { id: string; incident_id: string; recommended_scenario_id: string; scenario_name: string; confidence: string; rationale: string | null; assumptions: Record<string, unknown>[]; risks: Record<string, unknown>[]; structured_summary: Record<string, unknown>; created_at: string };
export type DecisionData = { scenarios: Scenario[]; recommendations: Recommendation[] };
export type Approval = { id: string; recommendation_id: string; incident_id: string | null; status: string; required_role: string; amount: string; currency: string; due_at: string | null; policy: Record<string, unknown>; created_at: string };
export type Execution = { id: string; action_type: string; adapter: string; status: string; attempt_count: number; parameters: Record<string, unknown>; external_reference: string | null; error: string | null; started_at: string | null; completed_at: string | null };
export type WorkflowVersion = { id: string; version: number; status: string; change_summary: string | null; published_at: string | null };
export type Workflow = { id: string; key: string; name: string; description: string | null; is_active: boolean; versions: WorkflowVersion[] };
export type WorkflowStage = { id: string; key: string; name: string; description: string | null; stage_type: string; handler: string; handler_version: string; position: number; is_enabled: boolean; configuration: Record<string, unknown>; retry_policy: Record<string, unknown>; timeout_seconds: number; failure_policy: string };
export type WorkflowDetail = { definition: { id: string; key: string; name: string; description: string | null }; version: WorkflowVersion; stages: WorkflowStage[]; dependencies: { id: string; stage_id: string; depends_on_stage_id: string }[]; available_handlers: string[] };
export type SettingsData = { integrations: { id: string; key: string; name: string; type: string; adapter: string; status: string; last_sync_at: string | null; last_error: string | null }[]; ai_models: { id: string; key: string; provider: string; model: string; is_enabled: boolean; parameters: Record<string, unknown>; secret_reference: string | null }[]; prompt_templates: { id: string; key: string; purpose: string; version: number; status: string }[]; risk: Record<string, unknown>; optimization: Record<string, unknown> };
export type AuditEntry = { id: string; occurred_at: string; actor_user_id: string | null; action: string; entity_type: string; entity_id: string | null; request_id: string | null; before: Record<string, unknown> | null; after: Record<string, unknown> | null; metadata: Record<string, unknown> };
export type Simulation = { id: string; workflow_version_id: string; incident_id: string | null; status: string; parameters: Record<string, unknown>; started_at: string | null; completed_at: string | null; stages: { id: string; name: string; status: string; attempts: number; duration_ms: number | null; output: Record<string, unknown> }[] };

const apiUrl =
  process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

function serverHeaders(): HeadersInit {
  const headers: Record<string, string> = {};
  if (process.env.INTERNAL_API_TOKEN) headers["X-Internal-API-Token"] = process.env.INTERNAL_API_TOKEN;
  if (process.env.DEFAULT_ORGANIZATION_ID) headers["X-Organization-ID"] = process.env.DEFAULT_ORGANIZATION_ID;
  if (process.env.DEFAULT_USER_ID) headers["X-User-ID"] = process.env.DEFAULT_USER_ID;
  return headers;
}

export async function getHealth(): Promise<HealthPayload | null> {
  return getResource<HealthPayload>("/health/live");
}

export async function getOverview(): Promise<Overview | null> {
  return getResource<Overview>("/dashboard/overview");
}

export async function getCollection<T>(path: string): Promise<T[] | null> {
  return getResource<T[]>(path);
}

export async function getResource<T>(path: string): Promise<T | null> {
  try {
    const response = await fetch(`${apiUrl}${path}`, { cache: "no-store", headers: serverHeaders() });
    if (!response.ok) return null;
    return (await response.json() as Envelope<T>).data;
  } catch {
    return null;
  }
}

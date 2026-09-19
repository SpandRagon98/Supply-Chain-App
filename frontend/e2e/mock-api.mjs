import { createServer } from "node:http";

let simulations = [];
const scenario = { id: "scenario-1", incident_id: "incident-1", name: "Activate alternate source", status: "RECOMMENDED", incremental_cost: "165000", delay_days: "7", revenue_protected: "15600000", orders_protected: 12, feasibility_score: "0.74", objective_score: "0.89", assumptions: [{ statement: "Qualification remains valid" }], constraints: [{ name: "budget" }], actions: [] };
const version = { id: "version-1", version: 1, status: "PUBLISHED", change_summary: "Canonical response", published_at: "2026-09-15T08:00:00Z" };
const stages = ["Detect disruption", "Assess impact", "Score risk", "Generate scenarios", "Recommend action", "Route approval", "Execute mitigation", "Verify outcome"].map((name, position) => ({ id: `stage-${position}`, key: name.toLowerCase().replaceAll(" ", "-"), name, description: `${name} deterministically.`, stage_type: "CONTROL", handler: "detect-disruption", handler_version: "1.0", position, is_enabled: true, configuration: {}, retry_policy: { max_attempts: 1 }, timeout_seconds: 300, failure_policy: "FAIL_WORKFLOW" }));

function dataFor(path, method) {
  if (path === "/api/v1/decisions") return { scenarios: [scenario], recommendations: [{ id: "recommendation-1", incident_id: "incident-1", recommended_scenario_id: scenario.id, scenario_name: scenario.name, confidence: "0.88", rationale: "Protects the most revenue within budget.", assumptions: scenario.assumptions, risks: [], structured_summary: { objective: "MAX_REVENUE_PROTECTED" }, created_at: "2026-09-15T08:00:00Z" }] };
  if (path === "/api/v1/approvals" && method === "GET") return [{ id: "approval-1", recommendation_id: "recommendation-1", incident_id: "incident-1", status: "PENDING", required_role: "APPROVER", amount: "165000", currency: "INR", due_at: null, policy: {}, created_at: "2026-09-15T08:00:00Z" }];
  if (path === "/api/v1/approvals/approval-1/decision") return { id: "decision-1", status: "APPROVED" };
  if (path === "/api/v1/executions") return [{ id: "execution-1", action_type: "SWITCH_SUPPLIER", adapter: "mock.erp@1.0", status: "PENDING", attempt_count: 0, parameters: {}, external_reference: null, error: null, started_at: null, completed_at: null }];
  if (path === "/api/v1/workflows") return [{ id: "workflow-1", key: "disruption-response", name: "Disruption response", description: "Governed response flow", is_active: true, versions: [version] }];
  if (path === "/api/v1/workflow-versions/version-1") return { definition: { id: "workflow-1", key: "disruption-response", name: "Disruption response", description: "Governed response flow" }, version, stages, dependencies: stages.slice(1).map((stage, index) => ({ id: `edge-${index}`, stage_id: stage.id, depends_on_stage_id: stages[index].id })), available_handlers: ["detect-disruption"] };
  if (path === "/api/v1/settings") return { integrations: [{ id: "connector-1", key: "nova-erp", name: "Nova ERP", type: "ERP", adapter: "mock.erp@1.0", status: "MOCK_MODE", last_sync_at: null, last_error: null }], ai_models: [], prompt_templates: [], risk: {}, optimization: {} };
  if (path === "/api/v1/audit-logs") return [];
  if (path === "/api/v1/simulations" && method === "POST") { simulations = [{ id: "simulation-1", workflow_version_id: version.id, incident_id: null, status: "SUCCEEDED", parameters: {}, started_at: "2026-09-15T08:00:00Z", completed_at: "2026-09-15T08:00:01Z", stages: stages.map((stage) => ({ id: `run-${stage.id}`, name: stage.name, status: "SUCCEEDED", attempts: 1, duration_ms: 4, output: {} })) }]; return { run_id: "simulation-1", status: "SUCCEEDED", context: {} }; }
  if (path === "/api/v1/simulations") return simulations;
  return [];
}

createServer((request, response) => {
  request.on("data", () => {});
  request.on("end", () => {
    const path = new URL(request.url, "http://127.0.0.1").pathname;
    if (path === "/api/v1/simulations/stream") {
      simulations = [{ id: "simulation-1", workflow_version_id: version.id, incident_id: null, status: "SUCCEEDED", parameters: {}, started_at: "2026-09-15T08:00:00Z", completed_at: "2026-09-15T08:00:01Z", stages: stages.map((stage) => ({ id: `run-${stage.id}`, name: stage.name, status: "SUCCEEDED", attempts: 1, duration_ms: 4, output: {} })) }];
      response.writeHead(200, { "Content-Type": "application/x-ndjson" });
      let index = 0;
      const timer = setInterval(() => {
        if (index < stages.length) {
          const stage = stages[index++];
          response.write(`${JSON.stringify({ type: "stage", id: `run-${stage.id}`, name: stage.name, status: "SUCCEEDED", attempts: 1, duration_ms: 4 })}\n`);
        } else {
          clearInterval(timer);
          response.end(`${JSON.stringify({ type: "complete", run_id: "simulation-1", status: "SUCCEEDED" })}\n`);
        }
      }, 20);
      return;
    }
    if (path === "/api/v1/suppliers") {
      response.writeHead(503, { "Content-Type": "application/json" });
      response.end(JSON.stringify({ error: { code: "unavailable", message: "Unavailable" } }));
      return;
    }
    const data = dataFor(path, request.method) ?? [];
    response.writeHead(200, { "Content-Type": "application/json" });
    response.end(JSON.stringify({ data, meta: { request_id: "e2e" } }));
  });
}).listen(4010, "127.0.0.1");

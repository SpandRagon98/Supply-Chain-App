"""Decision, workflow, configuration, audit, and simulation control-plane APIs."""

import asyncio
import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import ResponseEnvelope, ResponseMeta
from app.api.v1.operations import Tenant, _limit
from app.domain.enums import ApprovalStatus, FailurePolicy
from app.domain.models import (
    ApprovalRequest,
    AuditLog,
    Connector,
    ExecutionAction,
    ExecutionResult,
    LLMModelConfiguration,
    PromptTemplate,
    Recommendation,
    Scenario,
    ScenarioAction,
    StageDefinition,
    StageRun,
    WorkflowDefinition,
    WorkflowRun,
    WorkflowVersion,
)
from app.infrastructure.database import get_db_session
from app.repositories.workflows import WorkflowRepository
from app.services.recommendations import ApprovalService
from app.services.workflows import StageDraft, WorkflowService
from app.workflows.default_handlers import BUILT_IN_STAGE_HANDLERS, create_stage_registry
from app.workflows.engine import WorkflowEngine

router = APIRouter(tags=["control-plane"])
Session = Annotated[AsyncSession, Depends(get_db_session)]


def default_retry_policy() -> dict[str, object]:
    return {"max_attempts": 1}


def envelope(request: Request, data: object) -> ResponseEnvelope[object]:
    return ResponseEnvelope(data=data, meta=ResponseMeta(request_id=request.state.request_id))


class ApprovalDecisionInput(BaseModel):
    decision: Literal["APPROVED", "REJECTED"]
    comment: str | None = Field(default=None, max_length=2000)


class WorkflowInput(BaseModel):
    key: str = Field(min_length=2, max_length=100, pattern=r"^[a-z0-9-]+$")
    name: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=2000)


class StageInput(BaseModel):
    key: str = Field(min_length=2, max_length=100, pattern=r"^[a-z0-9-]+$")
    name: str = Field(min_length=2, max_length=200)
    stage_type: str = Field(min_length=2, max_length=80)
    handler: str
    position: int = Field(ge=0)
    description: str | None = None
    configuration: dict[str, object] = Field(default_factory=dict)


class StageEnabledInput(BaseModel):
    enabled: bool


class StageConfigurationInput(BaseModel):
    configuration: dict[str, object] = Field(default_factory=dict)
    retry_policy: dict[str, object] = Field(default_factory=default_retry_policy)
    timeout_seconds: int = Field(default=300, ge=1, le=3600)
    failure_policy: FailurePolicy = FailurePolicy.FAIL_WORKFLOW


class DependencyInput(BaseModel):
    stage_id: UUID
    depends_on_stage_id: UUID


class SimulationInput(BaseModel):
    workflow_version_id: UUID
    incident_id: UUID | None = None
    parameters: dict[str, object] = Field(default_factory=dict)


@router.get("/decisions", response_model=ResponseEnvelope[object])
async def decisions(
    request: Request, session: Session, tenant: Tenant, incident_id: UUID | None = None
) -> ResponseEnvelope[object]:
    scenario_query = select(Scenario).where(Scenario.organization_id == tenant.organization_id)
    recommendation_query = select(Recommendation).where(
        Recommendation.organization_id == tenant.organization_id
    )
    if incident_id:
        scenario_query = scenario_query.where(Scenario.incident_id == incident_id)
        recommendation_query = recommendation_query.where(Recommendation.incident_id == incident_id)
    scenarios = list(
        (await session.scalars(scenario_query.order_by(Scenario.created_at.desc()))).all()
    )
    recommendations = list(
        (
            await session.scalars(recommendation_query.order_by(Recommendation.created_at.desc()))
        ).all()
    )
    scenario_actions = list(
        (
            await session.scalars(
                select(ScenarioAction).where(
                    ScenarioAction.organization_id == tenant.organization_id,
                    ScenarioAction.scenario_id.in_(
                        [item.id for item in scenarios] or [UUID(int=0)]
                    ),
                )
            )
        ).all()
    )
    actions_by_scenario: dict[UUID, list[dict[str, object]]] = {}
    for item in scenario_actions:
        actions_by_scenario.setdefault(item.scenario_id, []).append(
            {
                "id": str(item.id),
                "sequence": item.sequence,
                "action_type": item.action_type,
                "incremental_cost": str(item.incremental_cost),
                "expected_delay_days": str(item.expected_delay_days),
                "feasibility": item.feasibility,
            }
        )
    scenario_names = {item.id: item.name for item in scenarios}
    return envelope(
        request,
        {
            "scenarios": [
                {
                    "id": str(item.id),
                    "incident_id": str(item.incident_id),
                    "name": item.name,
                    "status": item.status.value,
                    "incremental_cost": str(item.incremental_cost),
                    "delay_days": str(item.delay_days),
                    "revenue_protected": str(item.revenue_protected),
                    "orders_protected": item.orders_protected,
                    "feasibility_score": str(item.feasibility_score),
                    "objective_score": str(item.objective_score) if item.objective_score else None,
                    "assumptions": item.assumptions,
                    "constraints": item.constraints,
                    "actions": actions_by_scenario.get(item.id, []),
                }
                for item in scenarios
            ],
            "recommendations": [
                {
                    "id": str(item.id),
                    "incident_id": str(item.incident_id),
                    "recommended_scenario_id": str(item.recommended_scenario_id),
                    "scenario_name": scenario_names.get(
                        item.recommended_scenario_id, "Unavailable scenario"
                    ),
                    "confidence": str(item.confidence),
                    "rationale": item.rationale,
                    "assumptions": item.assumptions,
                    "risks": item.risks,
                    "structured_summary": item.structured_summary,
                    "created_at": item.created_at.isoformat(),
                }
                for item in recommendations
            ],
        },
    )


@router.get("/approvals", response_model=ResponseEnvelope[object])
async def approvals(
    request: Request, session: Session, tenant: Tenant, limit: int = 100
) -> ResponseEnvelope[object]:
    rows = list(
        (
            await session.scalars(
                select(ApprovalRequest)
                .where(ApprovalRequest.organization_id == tenant.organization_id)
                .order_by(ApprovalRequest.created_at.desc())
                .limit(_limit(limit))
            )
        ).all()
    )
    recommendation_ids = [item.recommendation_id for item in rows]
    recommendations = {
        item.id: item
        for item in (
            await session.scalars(
                select(Recommendation).where(
                    Recommendation.organization_id == tenant.organization_id,
                    Recommendation.id.in_(recommendation_ids or [UUID(int=0)]),
                )
            )
        ).all()
    }
    return envelope(
        request,
        [
            {
                "id": str(item.id),
                "recommendation_id": str(item.recommendation_id),
                "incident_id": str(recommendations[item.recommendation_id].incident_id)
                if item.recommendation_id in recommendations
                else None,
                "status": item.status.value,
                "required_role": item.required_role_key,
                "amount": str(item.amount),
                "currency": item.currency,
                "due_at": item.due_at.isoformat() if item.due_at else None,
                "policy": item.policy_snapshot,
                "created_at": item.created_at.isoformat(),
            }
            for item in rows
        ],
    )


@router.post("/approvals/{approval_id}/decision", response_model=ResponseEnvelope[object])
async def decide_approval(
    request: Request,
    approval_id: UUID,
    payload: ApprovalDecisionInput,
    session: Session,
    tenant: Tenant,
) -> ResponseEnvelope[object]:
    approval = await session.scalar(
        select(ApprovalRequest).where(
            ApprovalRequest.organization_id == tenant.organization_id,
            ApprovalRequest.id == approval_id,
        )
    )
    if approval is None:
        raise HTTPException(status_code=404, detail="Approval request not found")
    if tenant.user_id is None:
        raise HTTPException(status_code=401, detail="An authenticated actor is required")
    try:
        result = await ApprovalService(session, tenant).decide(
            approval, ApprovalStatus(payload.decision), payload.comment
        )
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    session.add(
        AuditLog(
            organization_id=tenant.organization_id,
            occurred_at=datetime.now(UTC),
            actor_user_id=tenant.user_id,
            action="approval.decided",
            entity_type="approval_request",
            entity_id=approval.id,
            request_id=request.state.request_id,
            before={"status": "PENDING"},
            after={"status": payload.decision, "comment": payload.comment},
            metadata_={},
        )
    )
    return envelope(request, {"id": str(result.id), "status": approval.status.value})


@router.get("/executions", response_model=ResponseEnvelope[object])
async def executions(
    request: Request, session: Session, tenant: Tenant, limit: int = 100
) -> ResponseEnvelope[object]:
    rows = list(
        (
            await session.scalars(
                select(ExecutionAction)
                .where(ExecutionAction.organization_id == tenant.organization_id)
                .order_by(ExecutionAction.created_at.desc())
                .limit(_limit(limit))
            )
        ).all()
    )
    results = list(
        (
            await session.scalars(
                select(ExecutionResult).where(
                    ExecutionResult.organization_id == tenant.organization_id,
                    ExecutionResult.execution_action_id.in_(
                        [item.id for item in rows] or [UUID(int=0)]
                    ),
                )
            )
        ).all()
    )
    result_by_action = {item.execution_action_id: item for item in results}
    return envelope(
        request,
        [
            {
                "id": str(item.id),
                "action_type": item.action_type,
                "adapter": item.adapter_key,
                "status": item.status.value,
                "attempt_count": item.attempt_count,
                "parameters": item.parameters,
                "external_reference": result_by_action[item.id].external_reference
                if item.id in result_by_action
                else None,
                "error": result_by_action[item.id].error_message
                if item.id in result_by_action
                else None,
                "started_at": item.started_at.isoformat() if item.started_at else None,
                "completed_at": item.completed_at.isoformat() if item.completed_at else None,
            }
            for item in rows
        ],
    )


def workflow_service(session: AsyncSession, tenant: Tenant) -> WorkflowService:
    return WorkflowService(WorkflowRepository(session, tenant), tenant, create_stage_registry())


@router.get("/workflows", response_model=ResponseEnvelope[object])
async def workflows(request: Request, session: Session, tenant: Tenant) -> ResponseEnvelope[object]:
    definitions = list(
        (
            await session.scalars(
                select(WorkflowDefinition)
                .where(WorkflowDefinition.organization_id == tenant.organization_id)
                .order_by(WorkflowDefinition.name)
            )
        ).all()
    )
    versions = list(
        (
            await session.scalars(
                select(WorkflowVersion)
                .where(WorkflowVersion.organization_id == tenant.organization_id)
                .order_by(WorkflowVersion.version.desc())
            )
        ).all()
    )
    return envelope(
        request,
        [
            {
                "id": str(item.id),
                "key": item.key,
                "name": item.name,
                "description": item.description,
                "is_active": item.is_active,
                "versions": [
                    serialize_version(version)
                    for version in versions
                    if version.workflow_definition_id == item.id
                ],
            }
            for item in definitions
        ],
    )


@router.post("/workflows", response_model=ResponseEnvelope[object])
async def create_workflow(
    request: Request, payload: WorkflowInput, session: Session, tenant: Tenant
) -> ResponseEnvelope[object]:
    draft = await workflow_service(session, tenant).create_workflow(
        key=payload.key,
        name=payload.name,
        description=payload.description,
        change_summary="Initial draft",
    )
    return envelope(
        request, {"id": str(draft.definition.id), "version": serialize_version(draft.version)}
    )


@router.get("/workflow-versions/{version_id}", response_model=ResponseEnvelope[object])
async def workflow_version(
    request: Request, version_id: UUID, session: Session, tenant: Tenant
) -> ResponseEnvelope[object]:
    repository = WorkflowRepository(session, tenant)
    version = await repository.get_version(version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Workflow version not found")
    definition = await repository.get_definition(version.workflow_definition_id)
    stages = list(await repository.list_stages(version_id))
    configs = {
        item.stage_definition_id: item for item in await repository.list_configurations(version_id)
    }
    dependencies = list(await repository.list_dependencies(version_id))
    return envelope(
        request,
        {
            "definition": {
                "id": str(definition.id),
                "key": definition.key,
                "name": definition.name,
                "description": definition.description,
            }
            if definition
            else None,
            "version": serialize_version(version),
            "stages": [
                {
                    "id": str(item.id),
                    "key": item.key,
                    "name": item.name,
                    "description": item.description,
                    "stage_type": item.stage_type,
                    "handler": item.handler,
                    "handler_version": item.handler_version,
                    "position": item.position,
                    "is_enabled": item.is_enabled,
                    "configuration": configs[item.id].configuration if item.id in configs else {},
                    "retry_policy": configs[item.id].retry_policy if item.id in configs else {},
                    "timeout_seconds": configs[item.id].timeout_seconds
                    if item.id in configs
                    else 300,
                    "failure_policy": configs[item.id].failure_policy.value
                    if item.id in configs
                    else "FAIL_WORKFLOW",
                }
                for item in stages
            ],
            "dependencies": [
                {
                    "id": str(item.id),
                    "stage_id": str(item.stage_definition_id),
                    "depends_on_stage_id": str(item.depends_on_stage_id),
                }
                for item in dependencies
            ],
            "available_handlers": list(BUILT_IN_STAGE_HANDLERS),
        },
    )


@router.post("/workflow-versions/{version_id}/stages", response_model=ResponseEnvelope[object])
async def add_stage(
    request: Request,
    version_id: UUID,
    payload: StageInput,
    session: Session,
    tenant: Tenant,
) -> ResponseEnvelope[object]:
    if payload.handler not in BUILT_IN_STAGE_HANDLERS:
        raise HTTPException(status_code=422, detail="The selected stage handler is unavailable")
    stage = await workflow_service(session, tenant).add_stage(
        version_id,
        StageDraft(
            key=payload.key,
            name=payload.name,
            stage_type=payload.stage_type,
            handler=payload.handler,
            handler_version="1.0",
            position=payload.position,
            description=payload.description,
            configuration=payload.configuration,
            retry_policy={"max_attempts": 1},
        ),
    )
    return envelope(request, {"id": str(stage.id), "key": stage.key})


@router.patch("/workflow-stages/{stage_id}/enabled", response_model=ResponseEnvelope[object])
async def set_stage_enabled(
    request: Request,
    stage_id: UUID,
    payload: StageEnabledInput,
    session: Session,
    tenant: Tenant,
) -> ResponseEnvelope[object]:
    stage = await workflow_service(session, tenant).set_stage_enabled(
        stage_id, enabled=payload.enabled
    )
    return envelope(request, {"id": str(stage.id), "is_enabled": stage.is_enabled})


@router.patch("/workflow-stages/{stage_id}/configuration", response_model=ResponseEnvelope[object])
async def update_stage_configuration(
    request: Request,
    stage_id: UUID,
    payload: StageConfigurationInput,
    session: Session,
    tenant: Tenant,
) -> ResponseEnvelope[object]:
    config = await workflow_service(session, tenant).update_configuration(
        stage_id,
        configuration=payload.configuration,
        retry_policy=payload.retry_policy,
        timeout_seconds=payload.timeout_seconds,
        failure_policy=payload.failure_policy,
    )
    return envelope(request, {"id": str(config.id), "configuration": config.configuration})


@router.post(
    "/workflow-versions/{version_id}/dependencies", response_model=ResponseEnvelope[object]
)
async def add_dependency(
    request: Request,
    version_id: UUID,
    payload: DependencyInput,
    session: Session,
    tenant: Tenant,
) -> ResponseEnvelope[object]:
    dependency = await workflow_service(session, tenant).add_dependency(
        version_id,
        stage_id=payload.stage_id,
        depends_on_stage_id=payload.depends_on_stage_id,
    )
    return envelope(request, {"id": str(dependency.id)})


@router.post("/workflow-versions/{version_id}/validate", response_model=ResponseEnvelope[object])
async def validate_workflow(
    request: Request, version_id: UUID, session: Session, tenant: Tenant
) -> ResponseEnvelope[object]:
    graph = await workflow_service(session, tenant).validate_version(version_id)
    return envelope(
        request, {"valid": True, "execution_order": [str(item) for item in graph.execution_order]}
    )


@router.post("/workflow-versions/{version_id}/publish", response_model=ResponseEnvelope[object])
async def publish_workflow(
    request: Request, version_id: UUID, session: Session, tenant: Tenant
) -> ResponseEnvelope[object]:
    version = await workflow_service(session, tenant).publish_version(version_id)
    return envelope(request, serialize_version(version))


@router.post("/workflow-versions/{version_id}/clone", response_model=ResponseEnvelope[object])
async def clone_workflow(
    request: Request, version_id: UUID, session: Session, tenant: Tenant
) -> ResponseEnvelope[object]:
    version = await workflow_service(session, tenant).clone_version(
        version_id, change_summary="Draft cloned from published version"
    )
    return envelope(request, serialize_version(version))


@router.get("/settings", response_model=ResponseEnvelope[object])
async def settings(request: Request, session: Session, tenant: Tenant) -> ResponseEnvelope[object]:
    connectors = list(
        (
            await session.scalars(
                select(Connector)
                .where(Connector.organization_id == tenant.organization_id)
                .order_by(Connector.name)
            )
        ).all()
    )
    models = list(
        (
            await session.scalars(
                select(LLMModelConfiguration)
                .where(LLMModelConfiguration.organization_id == tenant.organization_id)
                .order_by(LLMModelConfiguration.key)
            )
        ).all()
    )
    prompts = list(
        (
            await session.scalars(
                select(PromptTemplate)
                .where(PromptTemplate.organization_id == tenant.organization_id)
                .order_by(PromptTemplate.key, PromptTemplate.version.desc())
            )
        ).all()
    )
    return envelope(
        request,
        {
            "integrations": [
                {
                    "id": str(item.id),
                    "key": item.key,
                    "name": item.name,
                    "type": item.connector_type,
                    "adapter": item.adapter,
                    "status": item.status.value,
                    "last_sync_at": item.last_sync_at.isoformat() if item.last_sync_at else None,
                    "last_error": item.last_error,
                }
                for item in connectors
            ],
            "ai_models": [
                {
                    "id": str(item.id),
                    "key": item.key,
                    "provider": item.provider,
                    "model": item.model,
                    "is_enabled": item.is_enabled,
                    "parameters": item.parameters,
                    "secret_reference": item.secret_reference,
                }
                for item in models
            ],
            "prompt_templates": [
                {
                    "id": str(item.id),
                    "key": item.key,
                    "purpose": item.purpose,
                    "version": item.version,
                    "status": item.status.value,
                }
                for item in prompts
            ],
            "risk": {
                "weights": {
                    "severity": 0.30,
                    "revenue": 0.30,
                    "orders": 0.20,
                    "single_source": 0.20,
                },
                "bands": {"critical": 75, "high": 50, "medium": 25},
            },
            "optimization": {
                "default_objective": "MAX_REVENUE_PROTECTED",
                "objectives": ["MAX_REVENUE_PROTECTED", "MIN_INCREMENTAL_COST", "MIN_DELAY"],
            },
        },
    )


@router.get("/audit-logs", response_model=ResponseEnvelope[object])
async def audit_logs(
    request: Request,
    session: Session,
    tenant: Tenant,
    entity_type: str | None = None,
    action: str | None = None,
    limit: int = 100,
) -> ResponseEnvelope[object]:
    query = select(AuditLog).where(AuditLog.organization_id == tenant.organization_id)
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)
    if action:
        query = query.where(AuditLog.action == action)
    rows = list(
        (
            await session.scalars(query.order_by(AuditLog.occurred_at.desc()).limit(_limit(limit)))
        ).all()
    )
    return envelope(
        request,
        [
            {
                "id": str(item.id),
                "occurred_at": item.occurred_at.isoformat(),
                "actor_user_id": str(item.actor_user_id) if item.actor_user_id else None,
                "action": item.action,
                "entity_type": item.entity_type,
                "entity_id": str(item.entity_id) if item.entity_id else None,
                "request_id": item.request_id,
                "before": item.before,
                "after": item.after,
                "metadata": item.metadata_,
            }
            for item in rows
        ],
    )


@router.get("/simulations", response_model=ResponseEnvelope[object])
async def simulations(
    request: Request, session: Session, tenant: Tenant
) -> ResponseEnvelope[object]:
    runs = list(
        (
            await session.scalars(
                select(WorkflowRun)
                .where(
                    WorkflowRun.organization_id == tenant.organization_id,
                    WorkflowRun.is_simulation.is_(True),
                )
                .order_by(WorkflowRun.created_at.desc())
                .limit(50)
            )
        ).all()
    )
    stage_runs = list(
        (
            await session.scalars(
                select(StageRun).where(
                    StageRun.organization_id == tenant.organization_id,
                    StageRun.workflow_run_id.in_([item.id for item in runs] or [UUID(int=0)]),
                )
            )
        ).all()
    )
    stage_by_id = {
        item.id: item
        for item in (
            await session.scalars(
                select(StageDefinition).where(
                    StageDefinition.organization_id == tenant.organization_id
                )
            )
        ).all()
    }
    return envelope(request, [serialize_run(item, stage_runs, stage_by_id) for item in runs])


@router.post("/simulations", response_model=ResponseEnvelope[object])
async def run_simulation(
    request: Request, payload: SimulationInput, session: Session, tenant: Tenant
) -> ResponseEnvelope[object]:
    repository = WorkflowRepository(session, tenant)
    service = WorkflowService(repository, tenant, create_stage_registry())
    engine = WorkflowEngine(repository, service, create_stage_registry(), tenant)
    result = await engine.execute(
        payload.workflow_version_id,
        initial_context={"simulation": True, "parameters": payload.parameters},
        incident_id=payload.incident_id,
        is_simulation=True,
        simulation_parameters=payload.parameters,
    )
    return envelope(
        request,
        {"run_id": str(result.run_id), "status": result.status.value, "context": result.context},
    )


@router.post("/simulations/stream")
async def stream_simulation(
    payload: SimulationInput, session: Session, tenant: Tenant
) -> StreamingResponse:
    """Stream NDJSON stage completion events while the real engine executes."""

    repository = WorkflowRepository(session, tenant)
    registry = create_stage_registry()
    service = WorkflowService(repository, tenant, registry)
    engine = WorkflowEngine(repository, service, registry, tenant)
    stage_names = {
        item.id: item.name for item in await repository.list_stages(payload.workflow_version_id)
    }
    queue: asyncio.Queue[dict[str, object] | None] = asyncio.Queue()

    async def stage_completed(stage_run: StageRun) -> None:
        await queue.put(
            {
                "type": "stage",
                "id": str(stage_run.id),
                "name": stage_names.get(stage_run.stage_definition_id, "Unknown stage"),
                "status": stage_run.status.value,
                "attempts": stage_run.attempt_count,
                "duration_ms": stage_run.duration_ms,
            }
        )

    async def execute() -> None:
        try:
            result = await engine.execute(
                payload.workflow_version_id,
                initial_context={"simulation": True, "parameters": payload.parameters},
                incident_id=payload.incident_id,
                is_simulation=True,
                simulation_parameters=payload.parameters,
                on_stage_complete=stage_completed,
            )
            await queue.put(
                {
                    "type": "complete",
                    "run_id": str(result.run_id),
                    "status": result.status.value,
                }
            )
        except Exception:
            await queue.put({"type": "error", "message": "Simulation execution failed."})
        finally:
            await queue.put(None)

    async def events() -> AsyncIterator[str]:
        task = asyncio.create_task(execute())
        while True:
            event = await queue.get()
            if event is None:
                break
            yield json.dumps(event) + "\n"
        await task

    return StreamingResponse(events(), media_type="application/x-ndjson")


def serialize_version(version: WorkflowVersion) -> dict[str, object]:
    return {
        "id": str(version.id),
        "version": version.version,
        "status": version.status.value,
        "change_summary": version.change_summary,
        "published_at": version.published_at.isoformat() if version.published_at else None,
    }


def serialize_run(
    run: WorkflowRun,
    stage_runs: list[StageRun],
    stages: dict[UUID, StageDefinition],
) -> dict[str, object]:
    return {
        "id": str(run.id),
        "workflow_version_id": str(run.workflow_version_id),
        "incident_id": str(run.incident_id) if run.incident_id else None,
        "status": run.status.value,
        "parameters": run.simulation_parameters,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "stages": [
            {
                "id": str(item.id),
                "name": stages[item.stage_definition_id].name
                if item.stage_definition_id in stages
                else "Unknown stage",
                "status": item.status.value,
                "attempts": item.attempt_count,
                "duration_ms": item.duration_ms,
                "output": item.output_payload,
            }
            for item in stage_runs
            if item.workflow_run_id == run.id
        ],
    }

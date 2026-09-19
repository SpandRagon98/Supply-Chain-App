"""Control-plane serialization, handlers, and production identity tests."""

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.api.v1.control_plane import (
    WorkflowInput,
    clone_workflow,
    create_workflow,
    default_retry_policy,
    publish_workflow,
    record_audit,
    require_roles,
    serialize_run,
    serialize_version,
    validate_workflow,
)
from app.api.v1.operations import get_tenant_context
from app.domain.enums import RoleKey, RunStatus, WorkflowVersionStatus
from app.domain.models import StageDefinition, StageRun, WorkflowRun, WorkflowVersion
from app.domain.tenant import TenantContext
from app.workflows.contracts import StageExecutionContext
from app.workflows.default_handlers import ConfiguredStageHandler, create_stage_registry


def request_with_headers(headers: dict[str, str]) -> Request:
    return Request(
        {
            "type": "http",
            "headers": [(key.lower().encode(), value.encode()) for key, value in headers.items()],
        }
    )


class ScalarRows:
    def all(self) -> list[RoleKey]:
        return [RoleKey.ADMIN]


class IdentitySession:
    def __init__(self, organization_id: object, user_id: object) -> None:
        self.values = iter((organization_id, user_id))

    async def scalar(self, _statement: object) -> object:
        return next(self.values)

    async def scalars(self, _statement: object) -> ScalarRows:
        return ScalarRows()


class AuditSession:
    def __init__(self) -> None:
        self.entities: list[object] = []

    def add(self, entity: object) -> None:
        self.entities.append(entity)


class WorkflowMutationService:
    def __init__(self, version: WorkflowVersion, definition: object) -> None:
        self.version = version
        self.definition = definition

    async def create_workflow(self, **_values: object) -> object:
        return SimpleNamespace(definition=self.definition, version=self.version)

    async def publish_version(self, _version_id: object) -> WorkflowVersion:
        self.version.status = WorkflowVersionStatus.PUBLISHED
        self.version.published_at = datetime(2026, 9, 19, tzinfo=UTC)
        return self.version

    async def validate_version(self, _version_id: object) -> object:
        return SimpleNamespace(execution_order=(uuid4(), uuid4()))

    async def clone_version(self, _version_id: object, **_values: object) -> WorkflowVersion:
        self.version.status = WorkflowVersionStatus.DRAFT
        self.version.published_at = None
        return self.version


async def test_production_internal_identity_loads_persisted_roles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    organization_id, user_id = uuid4(), uuid4()
    monkeypatch.setattr(
        "app.api.v1.operations.get_settings",
        lambda: SimpleNamespace(is_production=True, internal_api_token="server-secret"),
    )
    tenant = await get_tenant_context(
        request_with_headers(
            {
                "X-Internal-API-Token": "server-secret",
                "X-Organization-ID": str(organization_id),
                "X-User-ID": str(user_id),
            }
        ),
        IdentitySession(organization_id, user_id),  # type: ignore[arg-type]
    )

    assert tenant.organization_id == organization_id
    assert tenant.user_id == user_id
    assert tenant.roles == frozenset({RoleKey.ADMIN})


async def test_built_in_stage_handler_reports_success_and_approval_wait() -> None:
    context = StageExecutionContext(uuid4(), uuid4(), uuid4(), {"simulation": True})
    handler = ConfiguredStageHandler("assess-impact")

    completed = await handler.execute(context, {"summary": "Impact calculated"})
    waiting = await handler.execute(context, {"wait_for_approval": True})
    registry = create_stage_registry()

    assert completed.status is RunStatus.SUCCEEDED
    assert completed.output["summary"] == "Impact calculated"
    assert waiting.status is RunStatus.WAITING_FOR_APPROVAL
    assert registry.contains("verify-outcome", "1.0")


def test_control_plane_serializers_keep_lineage_shape() -> None:
    organization_id, version_id, definition_id = uuid4(), uuid4(), uuid4()
    version = WorkflowVersion(
        id=version_id,
        organization_id=organization_id,
        workflow_definition_id=definition_id,
        version=3,
        status=WorkflowVersionStatus.PUBLISHED,
        change_summary="Validated",
        published_at=datetime(2026, 9, 19, tzinfo=UTC),
    )
    stage = StageDefinition(
        id=uuid4(),
        organization_id=organization_id,
        workflow_version_id=version_id,
        key="assess-impact",
        name="Assess impact",
        stage_type="IMPACT",
        handler="assess-impact",
        handler_version="1.0",
        position=1,
        is_enabled=True,
        input_schema={},
        output_schema={},
        configuration_schema={},
    )
    run = WorkflowRun(
        id=uuid4(),
        organization_id=organization_id,
        workflow_version_id=version_id,
        status=RunStatus.SUCCEEDED,
        is_simulation=True,
        simulation_parameters={"delay_days": 5},
        context={},
    )
    stage_run = StageRun(
        id=uuid4(),
        organization_id=organization_id,
        workflow_run_id=run.id,
        stage_definition_id=stage.id,
        status=RunStatus.SUCCEEDED,
        attempt_count=1,
        input_payload={},
        output_payload={"revenue_at_risk": "100"},
        duration_ms=7,
    )

    assert serialize_version(version)["published_at"] == "2026-09-19T00:00:00+00:00"
    serialized = serialize_run(run, [stage_run], {stage.id: stage})
    assert serialized["parameters"] == {"delay_days": 5}
    assert serialized["stages"][0]["name"] == "Assess impact"  # type: ignore[index]
    assert default_retry_policy() == {"max_attempts": 1}


def test_control_plane_mutations_require_roles_and_emit_audit() -> None:
    organization_id, user_id, entity_id = uuid4(), uuid4(), uuid4()
    unauthorized = TenantContext(organization_id, user_id, frozenset({RoleKey.VIEWER}))
    authorized = TenantContext(organization_id, user_id, frozenset({RoleKey.ADMIN}))
    with pytest.raises(HTTPException, match="not authorized"):
        require_roles(unauthorized, RoleKey.ADMIN)
    require_roles(authorized, RoleKey.ADMIN)

    request = request_with_headers({})
    request.state.request_id = "quality-review"
    session = AuditSession()
    record_audit(
        session,  # type: ignore[arg-type]
        request,
        authorized,
        action="workflow.published",
        entity_type="workflow_version",
        entity_id=entity_id,
        after={"status": "PUBLISHED"},
        workflow_version_id=entity_id,
    )

    audit = session.entities[0]
    assert audit.action == "workflow.published"  # type: ignore[attr-defined]
    assert audit.request_id == "quality-review"  # type: ignore[attr-defined]


async def test_workflow_create_and_publish_are_authorized_and_audited(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    organization_id, user_id, definition_id, version_id = uuid4(), uuid4(), uuid4(), uuid4()
    tenant = TenantContext(organization_id, user_id, frozenset({RoleKey.ADMIN}))
    definition = SimpleNamespace(id=definition_id, key="recovery", name="Recovery")
    version = WorkflowVersion(
        id=version_id,
        organization_id=organization_id,
        workflow_definition_id=definition_id,
        version=1,
        status=WorkflowVersionStatus.DRAFT,
        change_summary="Initial draft",
    )
    service = WorkflowMutationService(version, definition)
    monkeypatch.setattr("app.api.v1.control_plane.workflow_service", lambda *_args: service)
    request = request_with_headers({})
    request.state.request_id = "workflow-mutation"
    session = AuditSession()

    created = await create_workflow(
        request,
        WorkflowInput(key="recovery", name="Recovery"),
        session,  # type: ignore[arg-type]
        tenant,
    )
    published = await publish_workflow(
        request,
        version_id,
        session,  # type: ignore[arg-type]
        tenant,
    )
    validated = await validate_workflow(request, version_id, session, tenant)  # type: ignore[arg-type]
    cloned = await clone_workflow(request, version_id, session, tenant)  # type: ignore[arg-type]

    assert created.data["id"] == str(definition_id)  # type: ignore[index]
    assert published.data["status"] == "PUBLISHED"  # type: ignore[index]
    assert validated.data["valid"] is True  # type: ignore[index]
    assert cloned.data["status"] == "DRAFT"  # type: ignore[index]
    assert [item.action for item in session.entities] == [  # type: ignore[attr-defined]
        "workflow.created",
        "workflow.published",
        "workflow.cloned",
    ]

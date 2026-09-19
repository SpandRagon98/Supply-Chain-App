"""Control-plane serialization, handlers, and production identity tests."""

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from starlette.requests import Request

from app.api.v1.control_plane import default_retry_policy, serialize_run, serialize_version
from app.api.v1.operations import get_tenant_context
from app.domain.enums import RoleKey, RunStatus, WorkflowVersionStatus
from app.domain.models import StageDefinition, StageRun, WorkflowRun, WorkflowVersion
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

"""Workflow DAG, registry, versioning, and execution tests."""

import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.errors import (
    PublishedWorkflowImmutableError,
    StageHandlerNotFoundError,
    WorkflowValidationError,
)
from app.domain.base import TenantEntity
from app.domain.enums import FailurePolicy, RunStatus, WorkflowVersionStatus
from app.domain.models import (
    Organization,
    StageConfiguration,
    StageDefinition,
    StageDependency,
    StageRun,
    User,
    WorkflowDefinition,
    WorkflowRun,
    WorkflowVersion,
)
from app.domain.tenant import TenantContext
from app.repositories.workflows import WorkflowRepository
from app.services.workflows import StageDraft, WorkflowService
from app.workflows.contracts import StageExecutionContext, StageResult
from app.workflows.dag import WorkflowGraphValidator
from app.workflows.engine import WorkflowEngine
from app.workflows.registry import StageRegistry


def make_stage(key: str, position: int, *, enabled: bool = True) -> StageDefinition:
    return StageDefinition(
        id=uuid4(),
        organization_id=uuid4(),
        workflow_version_id=uuid4(),
        key=key,
        name=key.title(),
        stage_type="TEST",
        handler=key,
        handler_version="1.0",
        position=position,
        is_enabled=enabled,
        input_schema={},
        output_schema={},
        configuration_schema={},
    )


def make_dependency(stage: StageDefinition, prerequisite: StageDefinition) -> StageDependency:
    return StageDependency(
        id=uuid4(),
        organization_id=stage.organization_id,
        workflow_version_id=stage.workflow_version_id,
        stage_definition_id=stage.id,
        depends_on_stage_id=prerequisite.id,
        condition={},
    )


def test_dag_validation_returns_stable_topological_order() -> None:
    ingest = make_stage("ingest", 10)
    normalize = make_stage("normalize", 20)
    resolve = make_stage("resolve", 30)
    incident = make_stage("incident", 40)
    dependencies = (
        make_dependency(normalize, ingest),
        make_dependency(resolve, ingest),
        make_dependency(incident, normalize),
        make_dependency(incident, resolve),
    )

    graph = WorkflowGraphValidator().validate((incident, resolve, ingest, normalize), dependencies)

    assert graph.execution_order == (ingest.id, normalize.id, resolve.id, incident.id)
    assert graph.roots == (ingest.id,)
    assert graph.leaves == (incident.id,)


@pytest.mark.parametrize(
    "mutate, expected_issue",
    [
        (
            lambda first, second: (make_dependency(first, second), make_dependency(second, first)),
            "cycle",
        ),
        (
            lambda first, _second: (make_dependency(first, first),),
            "cannot depend on itself",
        ),
    ],
)
def test_dag_validation_rejects_cycles_and_self_dependencies(
    mutate: object, expected_issue: str
) -> None:
    first = make_stage("first", 1)
    second = make_stage("second", 2)
    dependencies = mutate(first, second)  # type: ignore[operator]

    with pytest.raises(WorkflowValidationError, match=expected_issue):
        WorkflowGraphValidator().validate((first, second), dependencies)


def test_dag_validation_rejects_enabled_stage_depending_on_disabled_stage() -> None:
    disabled = make_stage("disabled", 1, enabled=False)
    enabled = make_stage("enabled", 2)

    with pytest.raises(WorkflowValidationError, match="cannot depend on disabled"):
        WorkflowGraphValidator().validate(
            (disabled, enabled), (make_dependency(enabled, disabled),)
        )


@dataclass
class PassHandler:
    key: str = "pass"
    version: str = "1.0"

    async def execute(
        self, context: StageExecutionContext, config: Mapping[str, object]
    ) -> StageResult:
        return StageResult(output={"seen": len(context.values), "config": dict(config)})


def test_stage_registry_is_versioned_and_rejects_duplicates() -> None:
    registry = StageRegistry()
    handler = PassHandler()
    registry.register(handler)

    assert registry.get("pass", "1.0") is handler
    assert registry.references == (("pass", "1.0"),)
    with pytest.raises(ValueError, match="already registered"):
        registry.register(handler)
    with pytest.raises(StageHandlerNotFoundError):
        registry.get("pass", "2.0")


def test_stage_result_only_allows_terminal_stage_outcomes() -> None:
    with pytest.raises(ValueError, match="succeed or wait"):
        StageResult(status=RunStatus.FAILED)


class MemoryWorkflowRepository(WorkflowRepository):
    """Small behavioral repository used to exercise services without PostgreSQL."""

    def __init__(self, tenant: TenantContext) -> None:
        self.tenant = tenant
        self.entities: list[object] = []

    async def add(self, entity: object) -> None:
        if not isinstance(entity, TenantEntity):
            raise TypeError("Memory workflow entities must be tenant scoped.")
        if getattr(entity, "organization_id", None) != self.tenant.organization_id:
            raise ValueError("Workflow entity does not belong to the active tenant.")
        entity.id = uuid4()
        self.entities.append(entity)

    async def flush(self) -> None:
        return None

    async def get_definition(self, definition_id: UUID) -> WorkflowDefinition | None:
        return next(
            (
                entity
                for entity in self.entities
                if isinstance(entity, WorkflowDefinition) and entity.id == definition_id
            ),
            None,
        )

    async def get_version(self, version_id: UUID) -> WorkflowVersion | None:
        return next(
            (
                entity
                for entity in self.entities
                if isinstance(entity, WorkflowVersion) and entity.id == version_id
            ),
            None,
        )

    async def get_stage(self, stage_id: UUID) -> StageDefinition | None:
        return next(
            (
                entity
                for entity in self.entities
                if isinstance(entity, StageDefinition) and entity.id == stage_id
            ),
            None,
        )

    async def list_stages(self, version_id: UUID) -> Sequence[StageDefinition]:
        return sorted(
            (
                entity
                for entity in self.entities
                if isinstance(entity, StageDefinition) and entity.workflow_version_id == version_id
            ),
            key=lambda stage: (stage.position, stage.key),
        )

    async def list_configurations(self, version_id: UUID) -> Sequence[StageConfiguration]:
        stage_ids = {stage.id for stage in await self.list_stages(version_id)}
        return [
            entity
            for entity in self.entities
            if isinstance(entity, StageConfiguration) and entity.stage_definition_id in stage_ids
        ]

    async def get_configuration(self, stage_id: UUID) -> StageConfiguration | None:
        return next(
            (
                entity
                for entity in self.entities
                if isinstance(entity, StageConfiguration) and entity.stage_definition_id == stage_id
            ),
            None,
        )

    async def list_dependencies(self, version_id: UUID) -> Sequence[StageDependency]:
        return [
            entity
            for entity in self.entities
            if isinstance(entity, StageDependency) and entity.workflow_version_id == version_id
        ]

    async def next_version_number(self, definition_id: UUID) -> int:
        versions = [
            entity.version
            for entity in self.entities
            if isinstance(entity, WorkflowVersion)
            and entity.workflow_definition_id == definition_id
        ]
        return max(versions, default=0) + 1

    async def add_run(self, run: WorkflowRun) -> None:
        await self.add(run)


@dataclass
class SeedContextHandler:
    key: str = "seed-context"
    version: str = "1.0"

    async def execute(
        self, context: StageExecutionContext, config: Mapping[str, object]
    ) -> StageResult:
        value = config.get("value")
        return StageResult(output={"seeded": value}, context_updates={"value": value})


@dataclass
class RetryMultiplyHandler:
    attempts: int = 0
    key: str = "retry-multiply"
    version: str = "1.0"

    async def execute(
        self, context: StageExecutionContext, config: Mapping[str, object]
    ) -> StageResult:
        self.attempts += 1
        if self.attempts == 1:
            raise RuntimeError("transient test failure")
        value = context.values["value"]
        factor = config["factor"]
        assert isinstance(value, int)
        assert isinstance(factor, int)
        result = value * factor
        return StageResult(output={"result": result}, context_updates={"result": result})


@pytest.mark.asyncio
async def test_workflow_service_publishes_clones_and_executes_version() -> None:
    tenant = TenantContext(organization_id=uuid4(), user_id=uuid4())
    repository = MemoryWorkflowRepository(tenant)
    retry_handler = RetryMultiplyHandler()
    registry = StageRegistry()
    registry.register(SeedContextHandler())
    registry.register(retry_handler)
    service = WorkflowService(repository, tenant, registry)

    draft = await service.create_workflow(key="test-flow", name="Test Flow")
    seed_stage = await service.add_stage(
        draft.version.id,
        StageDraft(
            key="seed",
            name="Seed",
            stage_type="TEST",
            handler="seed-context",
            handler_version="1.0",
            position=10,
            configuration={"value": 7},
        ),
    )
    multiply_stage = await service.add_stage(
        draft.version.id,
        StageDraft(
            key="multiply",
            name="Multiply",
            stage_type="TEST",
            handler="retry-multiply",
            handler_version="1.0",
            position=20,
            configuration={"factor": 6},
            retry_policy={"max_attempts": 2},
        ),
    )
    await service.update_configuration(
        multiply_stage.id,
        configuration={"factor": 6},
        retry_policy={"max_attempts": 2},
        timeout_seconds=30,
        failure_policy=FailurePolicy.FAIL_WORKFLOW,
    )
    await service.add_dependency(
        draft.version.id,
        stage_id=multiply_stage.id,
        depends_on_stage_id=seed_stage.id,
    )

    published = await service.publish_version(draft.version.id)
    result = await WorkflowEngine(repository, service, registry, tenant).execute(
        published.id,
        initial_context={"source": "unit-test"},
        is_simulation=True,
    )
    clone = await service.clone_version(published.id, change_summary="Tune thresholds")

    assert published.status is WorkflowVersionStatus.PUBLISHED
    assert published.published_by_user_id == tenant.user_id
    assert result.status is RunStatus.SUCCEEDED
    assert result.context == {"source": "unit-test", "value": 7, "result": 42}
    assert retry_handler.attempts == 2
    assert clone.version == 2
    assert clone.status is WorkflowVersionStatus.DRAFT
    assert clone.cloned_from_version_id == published.id
    assert len(await repository.list_stages(clone.id)) == 2
    assert len(await repository.list_dependencies(clone.id)) == 1
    with pytest.raises(PublishedWorkflowImmutableError):
        await service.set_stage_enabled(seed_stage.id, enabled=False)
    archived = await service.archive_version(published.id)
    assert archived.status is WorkflowVersionStatus.ARCHIVED
    with pytest.raises(WorkflowValidationError, match="only published"):
        await WorkflowEngine(repository, service, registry, tenant).execute(archived.id)


@pytest.mark.asyncio
async def test_workflow_service_rejects_missing_handlers_and_invalid_drafts() -> None:
    tenant = TenantContext(organization_id=uuid4(), user_id=None)
    repository = MemoryWorkflowRepository(tenant)
    service = WorkflowService(repository, tenant, StageRegistry())
    draft = await service.create_workflow(key="invalid", name="Invalid")

    with pytest.raises(WorkflowValidationError, match="position cannot be negative"):
        await service.add_stage(
            draft.version.id,
            StageDraft(
                key="bad-position",
                name="Bad",
                stage_type="TEST",
                handler="missing",
                handler_version="1.0",
                position=-1,
            ),
        )

    stage = await service.add_stage(
        draft.version.id,
        StageDraft(
            key="missing-handler",
            name="Missing Handler",
            stage_type="TEST",
            handler="missing",
            handler_version="1.0",
            position=1,
        ),
    )
    with pytest.raises(WorkflowValidationError, match="unavailable handler"):
        await service.publish_version(draft.version.id)
    with pytest.raises(WorkflowValidationError, match="timeout"):
        await service.update_configuration(stage.id, configuration={}, timeout_seconds=0)


@pytest.mark.asyncio
async def test_postgresql_workflow_versioning_and_execution() -> None:
    database_url = os.getenv("TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip("TEST_DATABASE_URL is only configured for PostgreSQL CI integration tests")

    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    organization_id = uuid4()
    user_id = uuid4()
    retry_handler = RetryMultiplyHandler()
    registry = StageRegistry()
    registry.register(SeedContextHandler())
    registry.register(retry_handler)

    try:
        async with session_factory() as session:
            transaction = await session.begin()
            session.add(
                Organization(
                    id=organization_id,
                    name="Workflow Test Tenant",
                    slug=f"workflow-test-{organization_id}",
                )
            )
            session.add(
                User(
                    id=user_id,
                    organization_id=organization_id,
                    email=f"workflow-{user_id}@test.example",
                    display_name="Workflow Tester",
                )
            )
            await session.flush()

            tenant = TenantContext(organization_id=organization_id, user_id=user_id)
            repository = WorkflowRepository(session, tenant)
            service = WorkflowService(repository, tenant, registry)
            draft = await service.create_workflow(
                key="test-flow", name="Test Flow", change_summary="Initial contract"
            )
            seed_stage = await service.add_stage(
                draft.version.id,
                StageDraft(
                    key="seed",
                    name="Seed",
                    stage_type="TEST",
                    handler="seed-context",
                    handler_version="1.0",
                    position=10,
                    configuration={"value": 7},
                ),
            )
            multiply_stage = await service.add_stage(
                draft.version.id,
                StageDraft(
                    key="multiply",
                    name="Multiply",
                    stage_type="TEST",
                    handler="retry-multiply",
                    handler_version="1.0",
                    position=20,
                    configuration={"factor": 6},
                    retry_policy={"max_attempts": 2},
                    failure_policy=FailurePolicy.FAIL_WORKFLOW,
                ),
            )
            await service.add_dependency(
                draft.version.id,
                stage_id=multiply_stage.id,
                depends_on_stage_id=seed_stage.id,
            )
            published = await service.publish_version(draft.version.id)

            assert published.status is WorkflowVersionStatus.PUBLISHED
            with pytest.raises(PublishedWorkflowImmutableError):
                await service.set_stage_enabled(seed_stage.id, enabled=False)

            workflow_engine = WorkflowEngine(repository, service, registry, tenant)
            result = await workflow_engine.execute(
                published.id,
                initial_context={"source": "integration-test"},
                is_simulation=True,
            )
            clone = await service.clone_version(published.id, change_summary="Tune thresholds")
            clone_stages = await repository.list_stages(clone.id)
            clone_dependencies = await repository.list_dependencies(clone.id)
            persisted_runs = await session.scalar(
                select(func.count())
                .select_from(WorkflowRun)
                .where(WorkflowRun.organization_id == organization_id)
            )
            persisted_stage_runs = await session.scalar(
                select(func.count())
                .select_from(StageRun)
                .where(StageRun.organization_id == organization_id)
            )

            assert result.status is RunStatus.SUCCEEDED
            assert result.context == {
                "source": "integration-test",
                "value": 7,
                "result": 42,
            }
            assert retry_handler.attempts == 2
            assert clone.version == 2
            assert clone.status is WorkflowVersionStatus.DRAFT
            assert clone.cloned_from_version_id == published.id
            assert len(clone_stages) == 2
            assert len(clone_dependencies) == 1
            assert persisted_runs == 1
            assert persisted_stage_runs == 2
            await transaction.rollback()
    finally:
        await engine.dispose()

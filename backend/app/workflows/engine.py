"""Deterministic registry-driven workflow execution engine."""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from time import perf_counter
from uuid import UUID

from app.core.errors import WorkflowNotFoundError, WorkflowValidationError
from app.domain.enums import FailurePolicy, RunStatus, WorkflowVersionStatus
from app.domain.models import StageConfiguration, StageDefinition, StageRun, WorkflowRun
from app.domain.tenant import TenantContext
from app.repositories.workflows import WorkflowRepository
from app.services.workflows import WorkflowService
from app.workflows.contracts import StageExecutionContext
from app.workflows.registry import StageRegistry


@dataclass(frozen=True, slots=True)
class WorkflowExecutionResult:
    run_id: UUID
    status: RunStatus
    context: dict[str, object]


class WorkflowEngine:
    """Execute a published workflow DAG in deterministic topological order."""

    def __init__(
        self,
        repository: WorkflowRepository,
        service: WorkflowService,
        registry: StageRegistry,
        tenant: TenantContext,
    ) -> None:
        if repository.tenant != tenant or service.tenant != tenant:
            raise ValueError("Workflow engine dependencies must share the active tenant.")
        self.repository = repository
        self.service = service
        self.registry = registry
        self.tenant = tenant

    async def execute(
        self,
        version_id: UUID,
        *,
        initial_context: dict[str, object] | None = None,
        incident_id: UUID | None = None,
        replay_of_run_id: UUID | None = None,
        is_simulation: bool = False,
        simulation_parameters: dict[str, object] | None = None,
        on_stage_complete: Callable[[StageRun], Awaitable[None]] | None = None,
    ) -> WorkflowExecutionResult:
        version = await self.repository.get_version(version_id)
        if version is None:
            raise WorkflowNotFoundError("workflow version")
        if version.status is not WorkflowVersionStatus.PUBLISHED:
            raise WorkflowValidationError(("only published workflow versions can execute",))

        graph = await self.service.validate_version(version_id)
        stages = {stage.id: stage for stage in await self.repository.list_stages(version_id)}
        configurations = {
            config.stage_definition_id: config
            for config in await self.repository.list_configurations(version_id)
        }
        missing_configs = tuple(
            f"stage '{stages[stage_id].key}' has no configuration"
            for stage_id in graph.execution_order
            if stage_id not in configurations
        )
        if missing_configs:
            raise WorkflowValidationError(missing_configs)
        for stage_id in graph.execution_order:
            config = configurations[stage_id]
            self._max_attempts(config.retry_policy)
            if config.timeout_seconds < 1:
                raise WorkflowValidationError(("stage timeout must be at least one second",))

        context = dict(initial_context or {})
        run = WorkflowRun(
            organization_id=self.tenant.organization_id,
            workflow_version_id=version_id,
            incident_id=incident_id,
            replay_of_run_id=replay_of_run_id,
            status=RunStatus.RUNNING,
            is_simulation=is_simulation,
            simulation_parameters=dict(simulation_parameters or {}),
            context=context,
            started_at=datetime.now(UTC),
        )
        await self.repository.add_run(run)

        for stage_id in graph.execution_order:
            stage = stages[stage_id]
            config = configurations[stage_id]
            outcome = await self._execute_stage(
                run,
                stage,
                config,
                context,
                on_stage_complete=on_stage_complete,
            )
            context.update(outcome.context_updates)
            run.context = dict(context)
            await self.repository.flush()
            if outcome.status is RunStatus.WAITING_FOR_APPROVAL:
                run.status = RunStatus.WAITING_FOR_APPROVAL
                await self.repository.flush()
                return self._result(run, context)
            if (
                outcome.status is RunStatus.FAILED
                and config.failure_policy is FailurePolicy.FAIL_WORKFLOW
            ):
                run.status = RunStatus.FAILED
                run.completed_at = datetime.now(UTC)
                run.error_code = "stage_execution_failed"
                run.error_message = f"Stage '{stage.key}' failed."
                await self.repository.flush()
                return self._result(run, context)

        run.status = RunStatus.SUCCEEDED
        run.completed_at = datetime.now(UTC)
        await self.repository.flush()
        return self._result(run, context)

    async def _execute_stage(
        self,
        run: WorkflowRun,
        stage: StageDefinition,
        config: StageConfiguration,
        context: dict[str, object],
        *,
        on_stage_complete: Callable[[StageRun], Awaitable[None]] | None = None,
    ) -> "_StageOutcome":
        stage_run = StageRun(
            organization_id=self.tenant.organization_id,
            workflow_run_id=run.id,
            stage_definition_id=stage.id,
            status=RunStatus.RUNNING,
            attempt_count=0,
            input_payload=dict(context),
            output_payload={},
            started_at=datetime.now(UTC),
        )
        await self.repository.add(stage_run)
        handler = self.registry.get(stage.handler, stage.handler_version)
        max_attempts = self._max_attempts(config.retry_policy)
        started = perf_counter()

        for attempt in range(1, max_attempts + 1):
            stage_run.attempt_count = attempt
            try:
                execution_context = StageExecutionContext(
                    organization_id=self.tenant.organization_id,
                    workflow_run_id=run.id,
                    stage_run_id=stage_run.id,
                    values=dict(context),
                )
                async with asyncio.timeout(config.timeout_seconds):
                    result = await handler.execute(execution_context, config.configuration)
                stage_run.status = result.status
                stage_run.output_payload = dict(result.output)
                stage_run.error_code = None
                stage_run.error_message = None
                stage_run.completed_at = datetime.now(UTC)
                stage_run.duration_ms = round((perf_counter() - started) * 1000)
                await self.repository.flush()
                if on_stage_complete is not None:
                    await on_stage_complete(stage_run)
                return _StageOutcome(
                    status=result.status,
                    context_updates=dict(result.context_updates),
                )
            except Exception as error:  # noqa: BLE001 - persisted as controlled stage failure
                stage_run.error_code = type(error).__name__
                stage_run.error_message = str(error)[:2000]
                if attempt == max_attempts:
                    stage_run.status = RunStatus.FAILED
                    stage_run.completed_at = datetime.now(UTC)
                    stage_run.duration_ms = round((perf_counter() - started) * 1000)
                    await self.repository.flush()
                    if on_stage_complete is not None:
                        await on_stage_complete(stage_run)
                    return _StageOutcome(status=RunStatus.FAILED)
                await self.repository.flush()

        raise AssertionError("The bounded retry loop must return an outcome.")

    @staticmethod
    def _max_attempts(retry_policy: dict[str, object]) -> int:
        configured = retry_policy.get("max_attempts", 1)
        if isinstance(configured, bool) or not isinstance(configured, int):
            raise WorkflowValidationError(("retry max_attempts must be an integer",))
        if configured < 1 or configured > 10:
            raise WorkflowValidationError(("retry max_attempts must be between 1 and 10",))
        return configured

    @staticmethod
    def _result(run: WorkflowRun, context: dict[str, object]) -> WorkflowExecutionResult:
        return WorkflowExecutionResult(run_id=run.id, status=run.status, context=dict(context))


@dataclass(frozen=True, slots=True)
class _StageOutcome:
    status: RunStatus
    context_updates: dict[str, object] = field(default_factory=dict)

"""Workflow authoring, validation, publication, and version cloning."""

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from app.core.errors import (
    PublishedWorkflowImmutableError,
    WorkflowNotFoundError,
    WorkflowValidationError,
)
from app.domain.enums import FailurePolicy, WorkflowVersionStatus
from app.domain.models import (
    StageConfiguration,
    StageDefinition,
    StageDependency,
    WorkflowDefinition,
    WorkflowVersion,
)
from app.domain.tenant import TenantContext
from app.repositories.workflows import WorkflowRepository
from app.workflows.dag import WorkflowGraph, WorkflowGraphValidator
from app.workflows.registry import StageRegistry


@dataclass(frozen=True, slots=True)
class StageDraft:
    key: str
    name: str
    stage_type: str
    handler: str
    handler_version: str
    position: int
    description: str | None = None
    is_enabled: bool = True
    input_schema: dict[str, object] = field(default_factory=dict)
    output_schema: dict[str, object] = field(default_factory=dict)
    configuration_schema: dict[str, object] = field(default_factory=dict)
    configuration: dict[str, object] = field(default_factory=dict)
    retry_policy: dict[str, object] = field(default_factory=dict)
    timeout_seconds: int = 300
    failure_policy: FailurePolicy = FailurePolicy.FAIL_WORKFLOW
    approval_requirements: dict[str, object] = field(default_factory=dict)
    ai_configuration: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class WorkflowDraft:
    definition: WorkflowDefinition
    version: WorkflowVersion


class WorkflowService:
    """The only supported mutation boundary for persisted workflow versions."""

    def __init__(
        self,
        repository: WorkflowRepository,
        tenant: TenantContext,
        registry: StageRegistry,
        validator: WorkflowGraphValidator | None = None,
    ) -> None:
        if repository.tenant != tenant:
            raise ValueError("Repository and service tenant contexts must match.")
        self.repository = repository
        self.tenant = tenant
        self.registry = registry
        self.validator = validator or WorkflowGraphValidator()

    async def create_workflow(
        self,
        *,
        key: str,
        name: str,
        description: str | None = None,
        change_summary: str | None = None,
    ) -> WorkflowDraft:
        definition = WorkflowDefinition(
            organization_id=self.tenant.organization_id,
            key=key,
            name=name,
            description=description,
            is_active=True,
        )
        await self.repository.add(definition)
        version = WorkflowVersion(
            organization_id=self.tenant.organization_id,
            workflow_definition_id=definition.id,
            version=1,
            status=WorkflowVersionStatus.DRAFT,
            change_summary=change_summary,
        )
        await self.repository.add(version)
        return WorkflowDraft(definition=definition, version=version)

    async def add_stage(self, version_id: UUID, draft: StageDraft) -> StageDefinition:
        await self._require_draft(version_id)
        if draft.position < 0:
            raise WorkflowValidationError(("stage position cannot be negative",))
        if draft.timeout_seconds < 1:
            raise WorkflowValidationError(("stage timeout must be at least one second",))
        stage = StageDefinition(
            organization_id=self.tenant.organization_id,
            workflow_version_id=version_id,
            key=draft.key,
            name=draft.name,
            description=draft.description,
            stage_type=draft.stage_type,
            handler=draft.handler,
            handler_version=draft.handler_version,
            position=draft.position,
            is_enabled=draft.is_enabled,
            input_schema=deepcopy(draft.input_schema),
            output_schema=deepcopy(draft.output_schema),
            configuration_schema=deepcopy(draft.configuration_schema),
        )
        await self.repository.add(stage)
        await self.repository.add(
            StageConfiguration(
                organization_id=self.tenant.organization_id,
                stage_definition_id=stage.id,
                configuration=deepcopy(draft.configuration),
                retry_policy=deepcopy(draft.retry_policy),
                timeout_seconds=draft.timeout_seconds,
                failure_policy=draft.failure_policy,
                approval_requirements=deepcopy(draft.approval_requirements),
                ai_configuration=deepcopy(draft.ai_configuration),
            )
        )
        return stage

    async def set_stage_enabled(self, stage_id: UUID, *, enabled: bool) -> StageDefinition:
        stage = await self._get_stage(stage_id)
        await self._require_draft(stage.workflow_version_id)
        stage.is_enabled = enabled
        await self.repository.flush()
        return stage

    async def update_configuration(
        self,
        stage_id: UUID,
        *,
        configuration: dict[str, object],
        retry_policy: dict[str, object] | None = None,
        timeout_seconds: int | None = None,
        failure_policy: FailurePolicy | None = None,
    ) -> StageConfiguration:
        stage = await self._get_stage(stage_id)
        await self._require_draft(stage.workflow_version_id)
        stage_config = await self.repository.get_configuration(stage.id)
        if stage_config is None:
            raise WorkflowNotFoundError("stage configuration")
        if timeout_seconds is not None and timeout_seconds < 1:
            raise WorkflowValidationError(("stage timeout must be at least one second",))
        stage_config.configuration = deepcopy(configuration)
        if retry_policy is not None:
            stage_config.retry_policy = deepcopy(retry_policy)
        if timeout_seconds is not None:
            stage_config.timeout_seconds = timeout_seconds
        if failure_policy is not None:
            stage_config.failure_policy = failure_policy
        await self.repository.flush()
        return stage_config

    async def add_dependency(
        self,
        version_id: UUID,
        *,
        stage_id: UUID,
        depends_on_stage_id: UUID,
        condition: dict[str, object] | None = None,
    ) -> StageDependency:
        await self._require_draft(version_id)
        stage = await self._get_stage(stage_id)
        prerequisite = await self._get_stage(depends_on_stage_id)
        if (
            stage.workflow_version_id != version_id
            or prerequisite.workflow_version_id != version_id
        ):
            raise WorkflowValidationError(
                ("dependency stages must belong to the same workflow version",)
            )
        dependency = StageDependency(
            organization_id=self.tenant.organization_id,
            workflow_version_id=version_id,
            stage_definition_id=stage_id,
            depends_on_stage_id=depends_on_stage_id,
            condition=deepcopy(condition or {}),
        )
        await self.repository.add(dependency)
        return dependency

    async def validate_version(self, version_id: UUID) -> WorkflowGraph:
        await self._get_version(version_id)
        stages = tuple(await self.repository.list_stages(version_id))
        dependencies = tuple(await self.repository.list_dependencies(version_id))
        graph = self.validator.validate(stages, dependencies)
        missing_handlers = tuple(
            f"stage '{stage.key}' references unavailable handler "
            f"'{stage.handler}' version '{stage.handler_version}'"
            for stage in stages
            if stage.is_enabled and not self.registry.contains(stage.handler, stage.handler_version)
        )
        if missing_handlers:
            raise WorkflowValidationError(missing_handlers)
        return graph

    async def publish_version(self, version_id: UUID) -> WorkflowVersion:
        version = await self._require_draft(version_id)
        await self.validate_version(version_id)
        version.status = WorkflowVersionStatus.PUBLISHED
        version.published_at = datetime.now(UTC)
        version.published_by_user_id = self.tenant.user_id
        await self.repository.flush()
        return version

    async def archive_version(self, version_id: UUID) -> WorkflowVersion:
        version = await self._get_version(version_id)
        if version.status is not WorkflowVersionStatus.PUBLISHED:
            raise WorkflowValidationError(("only published workflow versions can be archived",))
        version.status = WorkflowVersionStatus.ARCHIVED
        await self.repository.flush()
        return version

    async def clone_version(
        self,
        source_version_id: UUID,
        *,
        change_summary: str | None = None,
    ) -> WorkflowVersion:
        source = await self._get_version(source_version_id)
        clone = WorkflowVersion(
            organization_id=self.tenant.organization_id,
            workflow_definition_id=source.workflow_definition_id,
            version=await self.repository.next_version_number(source.workflow_definition_id),
            status=WorkflowVersionStatus.DRAFT,
            cloned_from_version_id=source.id,
            change_summary=change_summary,
        )
        await self.repository.add(clone)

        source_stages = tuple(await self.repository.list_stages(source.id))
        source_configs = {
            config.stage_definition_id: config
            for config in await self.repository.list_configurations(source.id)
        }
        stage_id_map: dict[UUID, UUID] = {}
        for old_stage in source_stages:
            new_stage = StageDefinition(
                organization_id=self.tenant.organization_id,
                workflow_version_id=clone.id,
                key=old_stage.key,
                name=old_stage.name,
                description=old_stage.description,
                stage_type=old_stage.stage_type,
                handler=old_stage.handler,
                handler_version=old_stage.handler_version,
                position=old_stage.position,
                is_enabled=old_stage.is_enabled,
                input_schema=deepcopy(old_stage.input_schema),
                output_schema=deepcopy(old_stage.output_schema),
                configuration_schema=deepcopy(old_stage.configuration_schema),
            )
            await self.repository.add(new_stage)
            stage_id_map[old_stage.id] = new_stage.id
            old_config = source_configs.get(old_stage.id)
            if old_config is not None:
                await self.repository.add(
                    StageConfiguration(
                        organization_id=self.tenant.organization_id,
                        stage_definition_id=new_stage.id,
                        configuration=deepcopy(old_config.configuration),
                        retry_policy=deepcopy(old_config.retry_policy),
                        timeout_seconds=old_config.timeout_seconds,
                        failure_policy=old_config.failure_policy,
                        approval_requirements=deepcopy(old_config.approval_requirements),
                        ai_configuration=deepcopy(old_config.ai_configuration),
                    )
                )

        for dependency in await self.repository.list_dependencies(source.id):
            await self.repository.add(
                StageDependency(
                    organization_id=self.tenant.organization_id,
                    workflow_version_id=clone.id,
                    stage_definition_id=stage_id_map[dependency.stage_definition_id],
                    depends_on_stage_id=stage_id_map[dependency.depends_on_stage_id],
                    condition=deepcopy(dependency.condition),
                )
            )
        return clone

    async def _get_version(self, version_id: UUID) -> WorkflowVersion:
        version = await self.repository.get_version(version_id)
        if version is None:
            raise WorkflowNotFoundError("workflow version")
        return version

    async def _require_draft(self, version_id: UUID) -> WorkflowVersion:
        version = await self._get_version(version_id)
        if version.status is not WorkflowVersionStatus.DRAFT:
            raise PublishedWorkflowImmutableError
        return version

    async def _get_stage(self, stage_id: UUID) -> StageDefinition:
        stage = await self.repository.get_stage(stage_id)
        if stage is None:
            raise WorkflowNotFoundError("workflow stage")
        return stage

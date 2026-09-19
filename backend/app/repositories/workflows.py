"""Tenant-scoped persistence operations for workflow aggregates."""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import (
    StageConfiguration,
    StageDefinition,
    StageDependency,
    WorkflowDefinition,
    WorkflowRun,
    WorkflowVersion,
)
from app.domain.tenant import TenantContext


class WorkflowRepository:
    """Keep every workflow aggregate query inside the active tenant."""

    def __init__(self, session: AsyncSession, tenant: TenantContext) -> None:
        self.session = session
        self.tenant = tenant

    async def add(self, entity: object) -> None:
        organization_id = getattr(entity, "organization_id", None)
        if organization_id != self.tenant.organization_id:
            raise ValueError("Workflow entity does not belong to the active tenant.")
        self.session.add(entity)
        await self.session.flush()

    async def flush(self) -> None:
        await self.session.flush()

    async def get_definition(self, definition_id: UUID) -> WorkflowDefinition | None:
        result = await self.session.execute(
            select(WorkflowDefinition).where(
                WorkflowDefinition.organization_id == self.tenant.organization_id,
                WorkflowDefinition.id == definition_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_version(self, version_id: UUID) -> WorkflowVersion | None:
        result = await self.session.execute(
            select(WorkflowVersion).where(
                WorkflowVersion.organization_id == self.tenant.organization_id,
                WorkflowVersion.id == version_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_stage(self, stage_id: UUID) -> StageDefinition | None:
        result = await self.session.execute(
            select(StageDefinition).where(
                StageDefinition.organization_id == self.tenant.organization_id,
                StageDefinition.id == stage_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_stages(self, version_id: UUID) -> Sequence[StageDefinition]:
        result = await self.session.scalars(
            select(StageDefinition)
            .where(
                StageDefinition.organization_id == self.tenant.organization_id,
                StageDefinition.workflow_version_id == version_id,
            )
            .order_by(StageDefinition.position, StageDefinition.key)
        )
        return result.all()

    async def list_configurations(self, version_id: UUID) -> Sequence[StageConfiguration]:
        result = await self.session.scalars(
            select(StageConfiguration)
            .join(StageDefinition, StageDefinition.id == StageConfiguration.stage_definition_id)
            .where(
                StageConfiguration.organization_id == self.tenant.organization_id,
                StageDefinition.workflow_version_id == version_id,
            )
        )
        return result.all()

    async def get_configuration(self, stage_id: UUID) -> StageConfiguration | None:
        result = await self.session.execute(
            select(StageConfiguration).where(
                StageConfiguration.organization_id == self.tenant.organization_id,
                StageConfiguration.stage_definition_id == stage_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_dependencies(self, version_id: UUID) -> Sequence[StageDependency]:
        result = await self.session.scalars(
            select(StageDependency).where(
                StageDependency.organization_id == self.tenant.organization_id,
                StageDependency.workflow_version_id == version_id,
            )
        )
        return result.all()

    async def next_version_number(self, definition_id: UUID) -> int:
        current = await self.session.scalar(
            select(func.max(WorkflowVersion.version)).where(
                WorkflowVersion.organization_id == self.tenant.organization_id,
                WorkflowVersion.workflow_definition_id == definition_id,
            )
        )
        return int(current or 0) + 1

    async def add_run(self, run: WorkflowRun) -> None:
        await self.add(run)

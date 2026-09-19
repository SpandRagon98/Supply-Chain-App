"""Tenant-scoped connector configuration and run persistence."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import TenantIsolationError
from app.domain.enums import RunStatus
from app.domain.models import Connector, ConnectorRun
from app.domain.tenant import TenantContext


class ConnectorRepository:
    def __init__(self, session: AsyncSession, tenant: TenantContext) -> None:
        self.session = session
        self.tenant = tenant

    async def get(self, connector_id: UUID) -> Connector | None:
        result = await self.session.execute(
            select(Connector).where(
                Connector.organization_id == self.tenant.organization_id,
                Connector.id == connector_id,
            )
        )
        return result.scalar_one_or_none()

    async def add(self, connector: Connector) -> Connector:
        if connector.organization_id != self.tenant.organization_id:
            raise TenantIsolationError
        self.session.add(connector)
        await self.session.flush()
        return connector

    async def add_run(self, run: ConnectorRun) -> ConnectorRun:
        if run.organization_id != self.tenant.organization_id:
            raise TenantIsolationError
        self.session.add(run)
        await self.session.flush()
        return run

    async def latest_successful_run(self, connector_id: UUID) -> ConnectorRun | None:
        result = await self.session.execute(
            select(ConnectorRun)
            .where(
                ConnectorRun.organization_id == self.tenant.organization_id,
                ConnectorRun.connector_id == connector_id,
                ConnectorRun.status == RunStatus.SUCCEEDED,
            )
            .order_by(ConnectorRun.completed_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def flush(self) -> None:
        await self.session.flush()

"""Tenant-scoped SQLAlchemy repository primitives."""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import TenantIsolationError
from app.domain.base import TenantEntity
from app.domain.tenant import TenantContext


class TenantRepository[ModelT: TenantEntity]:
    """Require organization scope for every read and mutation."""

    def __init__(
        self,
        session: AsyncSession,
        model_type: type[ModelT],
        tenant: TenantContext,
    ) -> None:
        self.session = session
        self.model_type = model_type
        self.tenant = tenant

    def scoped_select(self) -> Select[tuple[ModelT]]:
        """Build the non-optional organization predicate for this model."""

        return select(self.model_type).where(
            self.model_type.organization_id == self.tenant.organization_id
        )

    async def get(self, entity_id: UUID) -> ModelT | None:
        statement = self.scoped_select().where(self.model_type.id == entity_id)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list(self, *, offset: int = 0, limit: int = 100) -> Sequence[ModelT]:
        statement = (
            self.scoped_select()
            .order_by(self.model_type.created_at.desc())
            .offset(max(offset, 0))
            .limit(min(max(limit, 1), 500))
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def count(self) -> int:
        statement = select(func.count(self.model_type.id)).where(
            self.model_type.organization_id == self.tenant.organization_id
        )
        result = await self.session.execute(statement)
        return int(result.scalar_one())

    async def add(self, entity: ModelT) -> ModelT:
        self._assert_tenant(entity)
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def delete(self, entity: ModelT) -> None:
        self._assert_tenant(entity)
        await self.session.delete(entity)
        await self.session.flush()

    def _assert_tenant(self, entity: TenantEntity) -> None:
        if entity.organization_id != self.tenant.organization_id:
            raise TenantIsolationError

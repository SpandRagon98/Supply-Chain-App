"""Supplier persistence."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Supplier
from app.domain.tenant import TenantContext
from app.repositories.base import TenantRepository


class SupplierRepository(TenantRepository[Supplier]):
    def __init__(self, session: AsyncSession, tenant: TenantContext) -> None:
        super().__init__(session, Supplier, tenant)

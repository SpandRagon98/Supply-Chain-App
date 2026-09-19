"""Supplier application service demonstrating tenant-safe domain writes."""

from app.domain.enums import RecordStatus
from app.domain.models import Supplier
from app.domain.tenant import TenantContext
from app.repositories.suppliers import SupplierRepository


class SupplierService:
    def __init__(self, repository: SupplierRepository, tenant: TenantContext) -> None:
        if repository.tenant != tenant:
            raise ValueError("Repository and service tenant contexts must match.")
        self.repository = repository
        self.tenant = tenant

    async def create(
        self,
        *,
        code: str,
        name: str,
        country_code: str,
        criticality: int = 50,
    ) -> Supplier:
        supplier = Supplier(
            organization_id=self.tenant.organization_id,
            code=code,
            name=name,
            country_code=country_code,
            criticality=criticality,
            status=RecordStatus.ACTIVE,
        )
        return await self.repository.add(supplier)

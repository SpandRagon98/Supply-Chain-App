"""Tenant-scoped persistence inputs and results for network impact analysis."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import (
    BillOfMaterial,
    BOMComponent,
    ConsumptionHistory,
    Customer,
    CustomerOrder,
    CustomerOrderLine,
    DisruptionIncident,
    ImpactAssessment,
    ImpactMetric,
    IncidentEntity,
    InventorySnapshot,
    Material,
    MaterialSupplier,
    PurchaseOrder,
    Shipment,
    Supplier,
    SupplierSite,
)
from app.domain.tenant import TenantContext
from app.impact.calculator import ImpactSnapshot


class ImpactRepository:
    def __init__(self, session: AsyncSession, tenant: TenantContext) -> None:
        self.session, self.tenant = session, tenant

    async def snapshot(self, incident_id: UUID) -> ImpactSnapshot | None:
        incident = await self._one(DisruptionIncident, DisruptionIncident.id == incident_id)
        if incident is None:
            return None
        return ImpactSnapshot(
            incident=incident,
            incident_entities=tuple(
                await self._all(IncidentEntity, IncidentEntity.incident_id == incident_id)
            ),
            suppliers=tuple(await self._all(Supplier)),
            supplier_sites=tuple(await self._all(SupplierSite)),
            materials=tuple(await self._all(Material)),
            material_suppliers=tuple(await self._all(MaterialSupplier)),
            boms=tuple(await self._all(BillOfMaterial)),
            bom_components=tuple(await self._all(BOMComponent)),
            inventories=tuple(await self._all(InventorySnapshot)),
            consumption=tuple(await self._all(ConsumptionHistory)),
            customers=tuple(await self._all(Customer)),
            orders=tuple(await self._all(CustomerOrder)),
            order_lines=tuple(await self._all(CustomerOrderLine)),
            purchase_orders=tuple(await self._all(PurchaseOrder)),
            shipments=tuple(await self._all(Shipment)),
        )

    async def save(
        self,
        incident_id: UUID,
        summary: dict[str, object],
        metrics: tuple[object, ...],
        calculation_version: str,
    ) -> ImpactAssessment:
        assessment = ImpactAssessment(
            organization_id=self.tenant.organization_id,
            incident_id=incident_id,
            calculated_at=datetime.now(UTC),
            calculation_version=calculation_version,
            summary=summary,
        )
        self.session.add(assessment)
        await self.session.flush()
        for metric in metrics:
            self.session.add(
                ImpactMetric(
                    organization_id=self.tenant.organization_id,
                    assessment_id=assessment.id,
                    metric_key=metric.key,
                    numeric_value=metric.value,
                    unit=metric.unit,
                    currency=metric.currency,
                    lineage=list(metric.lineage),
                )
            )
        await self.session.flush()
        return assessment

    async def _all(self, model: type[object], *predicates: object) -> list[object]:
        result = await self.session.scalars(
            select(model).where(
                model.organization_id == self.tenant.organization_id, *predicates
            )
        )
        return list(result.all())

    async def _one(self, model: type[object], *predicates: object) -> object | None:
        result = await self.session.scalars(
            select(model).where(
                model.organization_id == self.tenant.organization_id, *predicates
            )
        )
        return result.one_or_none()

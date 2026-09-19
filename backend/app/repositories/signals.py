"""Tenant-scoped persistence for signals, entity candidates, and incidents."""

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import TenantIsolationError
from app.domain.base import TenantEntity
from app.domain.enums import IncidentStatus
from app.domain.models import (
    DisruptionIncident,
    ExternalSignal,
    Facility,
    IncidentEntity,
    IncidentSignal,
    Material,
    Shipment,
    SignalSource,
    Supplier,
    SupplierSite,
)
from app.domain.tenant import TenantContext
from app.intelligence.contracts import EntityCandidate


class SignalRepository:
    def __init__(self, session: AsyncSession, tenant: TenantContext) -> None:
        self.session = session
        self.tenant = tenant

    async def add[EntityT: TenantEntity](self, entity: EntityT) -> EntityT:
        if entity.organization_id != self.tenant.organization_id:
            raise TenantIsolationError
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def flush(self) -> None:
        await self.session.flush()

    async def get_source_by_key(self, key: str) -> SignalSource | None:
        result = await self.session.execute(
            select(SignalSource).where(
                SignalSource.organization_id == self.tenant.organization_id,
                SignalSource.key == key,
            )
        )
        return result.scalar_one_or_none()

    async def get_signal(self, source_id: UUID, external_id: str) -> ExternalSignal | None:
        result = await self.session.execute(
            select(ExternalSignal).where(
                ExternalSignal.organization_id == self.tenant.organization_id,
                ExternalSignal.source_id == source_id,
                ExternalSignal.external_id == external_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_incident(self, incident_id: UUID) -> DisruptionIncident | None:
        result = await self.session.execute(
            select(DisruptionIncident).where(
                DisruptionIncident.organization_id == self.tenant.organization_id,
                DisruptionIncident.id == incident_id,
            )
        )
        return result.scalar_one_or_none()

    async def find_open_incident(
        self,
        deduplication_key: str,
        earliest_started_at: datetime,
    ) -> DisruptionIncident | None:
        result = await self.session.execute(
            select(DisruptionIncident)
            .where(
                DisruptionIncident.organization_id == self.tenant.organization_id,
                DisruptionIncident.deduplication_key == deduplication_key,
                DisruptionIncident.started_at >= earliest_started_at,
                DisruptionIncident.status.notin_((IncidentStatus.RESOLVED, IncidentStatus.CLOSED)),
            )
            .order_by(DisruptionIncident.started_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_incident_signal(
        self, incident_id: UUID, signal_id: UUID
    ) -> IncidentSignal | None:
        result = await self.session.execute(
            select(IncidentSignal).where(
                IncidentSignal.organization_id == self.tenant.organization_id,
                IncidentSignal.incident_id == incident_id,
                IncidentSignal.signal_id == signal_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_incident_entity(
        self, incident_id: UUID, entity_type: str, entity_id: UUID
    ) -> IncidentEntity | None:
        result = await self.session.execute(
            select(IncidentEntity).where(
                IncidentEntity.organization_id == self.tenant.organization_id,
                IncidentEntity.incident_id == incident_id,
                IncidentEntity.entity_type == entity_type,
                IncidentEntity.entity_id == entity_id,
            )
        )
        return result.scalar_one_or_none()

    async def entity_candidates(self) -> tuple[EntityCandidate, ...]:
        suppliers = await self._all(Supplier)
        sites = await self._all(SupplierSite)
        materials = await self._all(Material)
        facilities = await self._all(Facility)
        shipments = await self._all(Shipment)
        candidates = [
            EntityCandidate("supplier", entity.id, (("code", entity.code), ("name", entity.name)))
            for entity in suppliers
        ]
        candidates.extend(
            EntityCandidate(
                "supplier_site",
                entity.id,
                (("code", entity.code), ("name", entity.name), ("city", entity.city)),
            )
            for entity in sites
        )
        candidates.extend(
            EntityCandidate("material", entity.id, (("sku", entity.sku), ("name", entity.name)))
            for entity in materials
        )
        candidates.extend(
            EntityCandidate(
                "facility",
                entity.id,
                (("code", entity.code), ("name", entity.name), ("city", entity.city)),
            )
            for entity in facilities
        )
        candidates.extend(
            EntityCandidate(
                "shipment",
                entity.id,
                (
                    ("shipment_number", entity.shipment_number),
                    ("tracking_reference", entity.tracking_reference or ""),
                ),
            )
            for entity in shipments
        )
        return tuple(candidates)

    async def _all[EntityT: TenantEntity](self, model_type: type[EntityT]) -> Sequence[EntityT]:
        result = await self.session.scalars(
            select(model_type).where(model_type.organization_id == self.tenant.organization_id)
        )
        return result.all()

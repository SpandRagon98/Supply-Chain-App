"""Tenant-scoped, read-only operational views for the frontend command center."""

from decimal import Decimal
from secrets import compare_digest
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import ResponseEnvelope, ResponseMeta
from app.core.config import get_settings
from app.domain.enums import IncidentStatus
from app.domain.models import (
    CustomerOrder,
    DisruptionIncident,
    ImpactAssessment,
    ImpactMetric,
    InventorySnapshot,
    Organization,
    RiskAssessment,
    Role,
    Scenario,
    Shipment,
    Supplier,
    User,
    UserRole,
)
from app.domain.tenant import TenantContext
from app.infrastructure.database import get_db_session

router = APIRouter(tags=["operations"])
Session = Annotated[AsyncSession, Depends(get_db_session)]


def _envelope(
    request: Request, data: dict[str, object] | list[dict[str, object]]
) -> ResponseEnvelope[object]:
    return ResponseEnvelope(data=data, meta=ResponseMeta(request_id=request.state.request_id))


async def get_tenant_context(request: Request, session: Session) -> TenantContext:
    """Accept explicit development tenancy; production must supply a real identity integration."""
    settings = get_settings()
    if settings.is_production:
        supplied_token = request.headers.get("X-Internal-API-Token")
        if (
            not settings.internal_api_token
            or not supplied_token
            or not compare_digest(supplied_token, settings.internal_api_token)
        ):
            raise HTTPException(status_code=401, detail="Authentication is required in production")
    raw_organization_id = request.headers.get("X-Organization-ID")
    if raw_organization_id:
        try:
            organization_id = UUID(raw_organization_id)
        except ValueError as error:
            raise HTTPException(
                status_code=400, detail="Invalid X-Organization-ID header"
            ) from error
        organization = await session.scalar(
            select(Organization.id).where(Organization.id == organization_id)
        )
        if organization is None:
            raise HTTPException(status_code=404, detail="Organization not found")
        tenant = await _actor_context(session, organization_id, request)
        if settings.is_production and tenant.user_id is None:
            raise HTTPException(status_code=401, detail="A valid user identity is required")
        return tenant
    if settings.is_production:
        raise HTTPException(status_code=401, detail="A tenant identity is required in production")
    demo_organization_id = await session.scalar(
        select(Organization.id).where(Organization.slug == "nova-electronics")
    )
    if demo_organization_id is None:
        raise HTTPException(status_code=503, detail="Demo organization has not been seeded")
    return await _actor_context(session, demo_organization_id, request)


async def _actor_context(
    session: AsyncSession, organization_id: UUID, request: Request
) -> TenantContext:
    raw_user_id = request.headers.get("X-User-ID")
    try:
        user_id = UUID(raw_user_id) if raw_user_id else None
    except ValueError as error:
        raise HTTPException(status_code=400, detail="Invalid X-User-ID header") from error
    if user_id is None:
        user_id = await session.scalar(
            select(User.id).where(
                User.organization_id == organization_id,
                User.email == "admin@nova.example",
            )
        )
    if user_id is None:
        return TenantContext(organization_id=organization_id, user_id=None)
    valid_user_id = await session.scalar(
        select(User.id).where(
            User.organization_id == organization_id,
            User.id == user_id,
            User.is_active.is_(True),
        )
    )
    if valid_user_id is None:
        return TenantContext(organization_id=organization_id, user_id=None)
    roles = await session.scalars(
        select(Role.key)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(
            Role.organization_id == organization_id,
            UserRole.organization_id == organization_id,
            UserRole.user_id == user_id,
        )
    )
    return TenantContext(
        organization_id=organization_id,
        user_id=valid_user_id,
        roles=frozenset(roles.all()),
    )


Tenant = Annotated[TenantContext, Depends(get_tenant_context)]


@router.get("/dashboard/overview", response_model=ResponseEnvelope[object])
async def dashboard_overview(
    request: Request, session: Session, tenant: Tenant
) -> ResponseEnvelope[object]:
    active_incidents = await session.scalar(
        select(func.count())
        .select_from(DisruptionIncident)
        .where(
            DisruptionIncident.organization_id == tenant.organization_id,
            DisruptionIncident.status.notin_((IncidentStatus.RESOLVED, IncidentStatus.CLOSED)),
        )
    )
    supplier_count = await session.scalar(
        select(func.count())
        .select_from(Supplier)
        .where(Supplier.organization_id == tenant.organization_id)
    )
    order_count = await session.scalar(
        select(func.count())
        .select_from(CustomerOrder)
        .where(CustomerOrder.organization_id == tenant.organization_id)
    )
    latest_metrics = await session.scalars(
        select(ImpactMetric).where(
            ImpactMetric.organization_id == tenant.organization_id,
            ImpactMetric.metric_key == "revenue_at_risk",
        )
    )
    revenue_at_risk = sum(
        (metric.numeric_value or Decimal(0) for metric in latest_metrics), Decimal(0)
    )
    return _envelope(
        request,
        {
            "active_incidents": active_incidents or 0,
            "suppliers": supplier_count or 0,
            "orders": order_count or 0,
            "revenue_at_risk": str(revenue_at_risk),
        },
    )


@router.get("/suppliers", response_model=ResponseEnvelope[object])
async def suppliers(
    request: Request, session: Session, tenant: Tenant, limit: int = 50
) -> ResponseEnvelope[object]:
    rows = await session.scalars(
        select(Supplier)
        .where(Supplier.organization_id == tenant.organization_id)
        .order_by(Supplier.name)
        .limit(_limit(limit))
    )
    return _envelope(
        request,
        [
            {
                "id": str(row.id),
                "code": row.code,
                "name": row.name,
                "country_code": row.country_code,
                "criticality": row.criticality,
                "status": row.status.value,
            }
            for row in rows
        ],
    )


@router.get("/inventory", response_model=ResponseEnvelope[object])
async def inventory(
    request: Request, session: Session, tenant: Tenant, limit: int = 50
) -> ResponseEnvelope[object]:
    rows = await session.scalars(
        select(InventorySnapshot)
        .where(InventorySnapshot.organization_id == tenant.organization_id)
        .order_by(InventorySnapshot.captured_at.desc())
        .limit(_limit(limit))
    )
    return _envelope(
        request,
        [
            {
                "id": str(row.id),
                "facility_id": str(row.facility_id),
                "material_id": str(row.material_id) if row.material_id else None,
                "product_id": str(row.product_id) if row.product_id else None,
                "captured_at": row.captured_at.isoformat(),
                "on_hand_quantity": str(row.on_hand_quantity),
                "allocated_quantity": str(row.allocated_quantity),
                "unit_of_measure": row.unit_of_measure,
            }
            for row in rows
        ],
    )


@router.get("/shipments", response_model=ResponseEnvelope[object])
async def shipments(
    request: Request, session: Session, tenant: Tenant, limit: int = 50
) -> ResponseEnvelope[object]:
    rows = await session.scalars(
        select(Shipment)
        .where(Shipment.organization_id == tenant.organization_id)
        .order_by(Shipment.created_at.desc())
        .limit(_limit(limit))
    )
    return _envelope(
        request,
        [
            {
                "id": str(row.id),
                "shipment_number": row.shipment_number,
                "status": row.status.value,
                "carrier": row.carrier,
                "transportation_mode": row.transportation_mode,
                "estimated_arrival_at": row.estimated_arrival_at.isoformat()
                if row.estimated_arrival_at
                else None,
            }
            for row in rows
        ],
    )


@router.get("/incidents", response_model=ResponseEnvelope[object])
async def incidents(
    request: Request, session: Session, tenant: Tenant, limit: int = 50
) -> ResponseEnvelope[object]:
    rows = await session.scalars(
        select(DisruptionIncident)
        .where(DisruptionIncident.organization_id == tenant.organization_id)
        .order_by(DisruptionIncident.started_at.desc())
        .limit(_limit(limit))
    )
    return _envelope(request, [_incident(row) for row in rows])


@router.get("/incidents/{incident_id}", response_model=ResponseEnvelope[object])
async def incident_detail(
    request: Request, incident_id: UUID, session: Session, tenant: Tenant
) -> ResponseEnvelope[object]:
    incident = await session.scalar(
        select(DisruptionIncident).where(
            DisruptionIncident.organization_id == tenant.organization_id,
            DisruptionIncident.id == incident_id,
        )
    )
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    impact = await session.scalar(
        select(ImpactAssessment)
        .where(
            ImpactAssessment.organization_id == tenant.organization_id,
            ImpactAssessment.incident_id == incident_id,
        )
        .order_by(ImpactAssessment.calculated_at.desc())
        .limit(1)
    )
    risk = await session.scalar(
        select(RiskAssessment)
        .where(
            RiskAssessment.organization_id == tenant.organization_id,
            RiskAssessment.incident_id == incident_id,
        )
        .order_by(RiskAssessment.calculated_at.desc())
        .limit(1)
    )
    scenarios = await session.scalars(
        select(Scenario)
        .where(
            Scenario.organization_id == tenant.organization_id, Scenario.incident_id == incident_id
        )
        .order_by(Scenario.created_at.desc())
    )
    return _envelope(
        request,
        {
            "incident": _incident(incident),
            "impact": impact.summary if impact else None,
            "risk": {
                "score": str(risk.score),
                "band": risk.band.value,
                "explanation": risk.explanation,
            }
            if risk
            else None,
            "scenarios": [
                {
                    "id": str(item.id),
                    "name": item.name,
                    "status": item.status.value,
                    "revenue_protected": str(item.revenue_protected),
                    "incremental_cost": str(item.incremental_cost),
                }
                for item in scenarios
            ],
        },
    )


def _limit(value: int) -> int:
    return min(max(value, 1), 100)


def _incident(row: DisruptionIncident) -> dict[str, object]:
    return {
        "id": str(row.id),
        "incident_number": row.incident_number,
        "title": row.title,
        "incident_type": row.incident_type.value,
        "severity": row.severity.value,
        "confidence": str(row.confidence),
        "status": row.status.value,
        "started_at": row.started_at.isoformat(),
    }

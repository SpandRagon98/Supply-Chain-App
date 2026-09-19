"""Tenant-scoped persistence for explainable risk assessments."""
# mypy: ignore-errors

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import (
    DisruptionIncident,
    ImpactAssessment,
    ImpactMetric,
    MaterialSupplier,
    RiskAssessment,
    RiskFactor,
    Supplier,
)
from app.domain.tenant import TenantContext
from app.risk.engine import RiskFactorValue, RiskResult


class RiskRepository:
    def __init__(self, session: AsyncSession, tenant: TenantContext) -> None:
        self.session, self.tenant = session, tenant

    async def inputs(
        self, incident_id: UUID, impact_assessment_id: UUID | None = None
    ) -> tuple[object, object | None, list[object], list[object], list[object]]:
        incident = await self._one(DisruptionIncident, DisruptionIncident.id == incident_id)
        if incident is None:
            return None, None, [], [], []
        statement = (
            select(ImpactAssessment)
            .where(
                ImpactAssessment.organization_id == self.tenant.organization_id,
                ImpactAssessment.incident_id == incident_id,
            )
            .order_by(ImpactAssessment.calculated_at.desc())
        )
        if impact_assessment_id is not None:
            statement = statement.where(ImpactAssessment.id == impact_assessment_id)
        impact = (await self.session.scalars(statement.limit(1))).first()
        metrics: list[object] = []
        if impact is not None:
            metrics = list(
                (
                    await self.session.scalars(
                        select(ImpactMetric).where(
                            ImpactMetric.organization_id == self.tenant.organization_id,
                            ImpactMetric.assessment_id == impact.id,
                        )
                    )
                ).all()
            )
        links = list(
            (
                await self.session.scalars(
                    select(MaterialSupplier).where(
                        MaterialSupplier.organization_id == self.tenant.organization_id
                    )
                )
            ).all()
        )
        suppliers = list(
            (
                await self.session.scalars(
                    select(Supplier).where(Supplier.organization_id == self.tenant.organization_id)
                )
            ).all()
        )
        return incident, impact, metrics, links, suppliers

    async def save(
        self, incident_id: UUID, impact_id: UUID | None, model_version: str, result: RiskResult
    ) -> RiskAssessment:
        assessment = RiskAssessment(
            organization_id=self.tenant.organization_id,
            incident_id=incident_id,
            impact_assessment_id=impact_id,
            score=result.score,
            band=result.band,
            model_version=model_version,
            explanation=result.explanation,
            calculated_at=datetime.now(UTC),
        )
        self.session.add(assessment)
        await self.session.flush()
        for factor in result.factors:
            self.session.add(self._factor(assessment.id, factor))
        await self.session.flush()
        return assessment

    def _factor(self, assessment_id: UUID, factor: RiskFactorValue) -> RiskFactor:
        return RiskFactor(
            organization_id=self.tenant.organization_id,
            risk_assessment_id=assessment_id,
            factor_key=factor.key,
            raw_value=factor.raw_value,
            normalized_value=factor.normalized_value,
            weight=factor.weight,
            contribution=factor.contribution,
            lineage=list(factor.lineage),
        )

    async def _one(self, model: type[object], *predicates: object) -> object | None:
        result = await self.session.scalars(
            select(model).where(model.organization_id == self.tenant.organization_id, *predicates)
        )  # type: ignore[attr-defined]
        return result.one_or_none()

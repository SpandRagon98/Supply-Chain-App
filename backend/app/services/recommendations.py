"""Persist deterministic recommendations, routes, and immutable approval decisions."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import ApprovalStatus, RoleKey
from app.domain.models import (
    ApprovalDecision,
    ApprovalRequest,
    Recommendation,
    RiskAssessment,
    Scenario,
)
from app.domain.tenant import TenantContext
from app.recommendations import ApprovalRouter, RecommendationEngine
from app.recommendations.engine import ScenarioSummary


class RecommendationService:
    def __init__(
        self,
        session: AsyncSession,
        tenant: TenantContext,
        engine: RecommendationEngine | None = None,
    ) -> None:
        self.session, self.tenant, self.engine = session, tenant, engine or RecommendationEngine()

    async def recommend(self, incident_id: UUID) -> Recommendation:
        scenarios = list(
            (
                await self.session.scalars(
                    select(Scenario).where(
                        Scenario.organization_id == self.tenant.organization_id,
                        Scenario.incident_id == incident_id,
                    )
                )
            ).all()
        )
        risk = (
            await self.session.scalars(
                select(RiskAssessment)
                .where(
                    RiskAssessment.organization_id == self.tenant.organization_id,
                    RiskAssessment.incident_id == incident_id,
                )
                .order_by(RiskAssessment.calculated_at.desc())
                .limit(1)
            )
        ).first()
        summaries = tuple(
            ScenarioSummary(
                str(item.id),
                item.name,
                item.incremental_cost,
                item.delay_days,
                item.revenue_protected,
                item.orders_protected,
                item.feasibility_score,
                item.objective_score,
                tuple(item.assumptions),
                tuple(item.constraints),
            )
            for item in scenarios
        )
        result = self.engine.recommend(summaries, risk.score if risk else None)
        recommendation = Recommendation(
            organization_id=self.tenant.organization_id,
            incident_id=incident_id,
            recommended_scenario_id=UUID(result.selected.id),
            confidence=result.confidence,
            rationale=result.rationale,
            alternative_scenario_ids=[item.id for item in result.alternatives],
            assumptions=list(result.selected.assumptions),
            risks=list(result.risks),
            structured_summary=result.structured_summary,
        )
        self.session.add(recommendation)
        await self.session.flush()
        return recommendation


class ApprovalService:
    def __init__(
        self, session: AsyncSession, tenant: TenantContext, router: ApprovalRouter | None = None
    ) -> None:
        self.session, self.tenant, self.router = session, tenant, router or ApprovalRouter.default()

    async def request(
        self,
        recommendation: Recommendation,
        amount: Decimal,
        currency: str,
        *,
        new_supplier: bool = False,
    ) -> ApprovalRequest:
        policy = self.router.route(amount, new_supplier=new_supplier)
        request = ApprovalRequest(
            organization_id=self.tenant.organization_id,
            recommendation_id=recommendation.id,
            status=ApprovalStatus.PENDING,
            requested_by_user_id=self.tenant.user_id,
            required_role_key=policy.required_role.value,
            amount=amount,
            currency=currency,
            policy_snapshot={
                "maximum_amount": str(policy.maximum_amount) if policy.maximum_amount else None,
                "required_role": policy.required_role.value,
                "new_supplier": new_supplier,
            },
        )
        self.session.add(request)
        await self.session.flush()
        return request

    async def decide(
        self, request: ApprovalRequest, decision: ApprovalStatus, comment: str | None = None
    ) -> ApprovalDecision:
        if decision not in {ApprovalStatus.APPROVED, ApprovalStatus.REJECTED}:
            raise ValueError("Approval decisions must be APPROVED or REJECTED")
        role = RoleKey(request.required_role_key)
        if not self.tenant.has_role(role, RoleKey.ADMIN):
            raise PermissionError("Actor is not authorized for this approval")
        if request.status is not ApprovalStatus.PENDING:
            raise ValueError("Only pending approvals can be decided")
        request.status = decision
        record = ApprovalDecision(
            organization_id=self.tenant.organization_id,
            approval_request_id=request.id,
            decided_by_user_id=self.tenant.user_id,
            decision=decision,
            comment=comment,
            decided_at=datetime.now(UTC),
        )
        self.session.add(record)
        await self.session.flush()
        return record

"""Generate transparent mitigation alternatives and persist the optimized choice."""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import ScenarioStatus
from app.domain.models import ImpactAssessment, ImpactMetric, Scenario, ScenarioAction
from app.domain.tenant import TenantContext
from app.optimization import OptimizationObjective, ScenarioCandidate, ScenarioOptimizer


class ScenarioService:
    def __init__(
        self,
        session: AsyncSession,
        tenant: TenantContext,
        optimizer: ScenarioOptimizer | None = None,
    ) -> None:
        self.session, self.tenant, self.optimizer = (
            session,
            tenant,
            optimizer or ScenarioOptimizer(),
        )

    async def generate_and_select(
        self, incident_id: UUID, objective: OptimizationObjective = OptimizationObjective.BALANCED
    ) -> list[Scenario]:
        impact = (
            await self.session.scalars(
                select(ImpactAssessment)
                .where(
                    ImpactAssessment.organization_id == self.tenant.organization_id,
                    ImpactAssessment.incident_id == incident_id,
                )
                .order_by(ImpactAssessment.calculated_at.desc())
                .limit(1)
            )
        ).first()
        metrics = (
            []
            if impact is None
            else list(
                (
                    await self.session.scalars(
                        select(ImpactMetric).where(
                            ImpactMetric.organization_id == self.tenant.organization_id,
                            ImpactMetric.assessment_id == impact.id,
                        )
                    )
                ).all()
            )
        )
        values = {metric.metric_key: Decimal(metric.numeric_value or 0) for metric in metrics}
        revenue, quantity, orders = (
            values.get("revenue_at_risk", Decimal(0)),
            values.get("quantity_at_risk", Decimal(0)),
            int(values.get("customer_orders_at_risk", Decimal(0))),
        )
        candidates = (
            ScenarioCandidate(
                "Wait and monitor",
                Decimal(0),
                Decimal(14),
                Decimal(0),
                Decimal(".15"),
                Decimal(".95"),
            ),
            ScenarioCandidate(
                "Expedite current supply",
                revenue * Decimal(".12"),
                Decimal(4),
                revenue * Decimal(".70"),
                Decimal(".75"),
                Decimal(".80"),
            ),
            ScenarioCandidate(
                "Switch to approved alternate",
                revenue * Decimal(".08"),
                Decimal(7),
                revenue * Decimal(".85"),
                Decimal(".70"),
                Decimal(".72"),
            ),
        )
        selected, score = self.optimizer.select(candidates, objective)
        scenarios: list[Scenario] = []
        for index, candidate in enumerate(candidates):
            protected_ratio = candidate.revenue_protected / revenue if revenue else Decimal(0)
            scenario = Scenario(
                organization_id=self.tenant.organization_id,
                incident_id=incident_id,
                name=candidate.name,
                description=f"Generated deterministic mitigation option for {objective.value}.",
                status=ScenarioStatus.RECOMMENDED if index == selected else ScenarioStatus.FEASIBLE,
                incremental_cost=candidate.incremental_cost,
                currency="INR",
                delay_days=candidate.delay_days,
                quantity_protected=quantity * protected_ratio,
                orders_protected=int(Decimal(orders) * protected_ratio),
                revenue_protected=candidate.revenue_protected,
                expected_service_level=candidate.expected_service_level,
                feasibility_score=candidate.feasibility_score,
                objective_score=score if index == selected else None,
                assumptions=[{"impact_assessment_id": str(impact.id) if impact else None}],
                constraints=[{"objective": objective.value}],
                calculation_lineage={"optimizer": "ortools-cbc", "objective": objective.value},
            )
            self.session.add(scenario)
            await self.session.flush()
            self.session.add(
                ScenarioAction(
                    organization_id=self.tenant.organization_id,
                    scenario_id=scenario.id,
                    sequence=1,
                    action_type=(
                        "MONITOR" if index == 0 else "EXPEDITE" if index == 1 else "SWITCH_SUPPLIER"
                    ),
                    parameters={},
                    incremental_cost=candidate.incremental_cost,
                    expected_delay_days=candidate.delay_days,
                    feasibility={"feasible": True},
                )
            )
            scenarios.append(scenario)
        await self.session.flush()
        return scenarios

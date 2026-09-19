"""Application service for risk scoring and durable factor explanations."""

from decimal import Decimal
from uuid import UUID

from app.core.errors import NotFoundError
from app.repositories.risk import RiskRepository
from app.risk import RiskEngine, RiskScoringConfig


class RiskService:
    def __init__(self, repository: RiskRepository, engine: RiskEngine | None = None) -> None:
        self.repository, self.engine = repository, engine or RiskEngine()

    async def assess(
        self,
        incident_id: UUID,
        config: RiskScoringConfig | None = None,
        impact_assessment_id: UUID | None = None,
    ) -> object:
        incident, impact, metrics, links, suppliers = await self.repository.inputs(
            incident_id, impact_assessment_id
        )
        if incident is None:
            raise NotFoundError("Disruption incident was not found")
        summary = getattr(impact, "summary", {}) if impact is not None else {}
        metric_values = {
            metric.metric_key: Decimal(metric.numeric_value or 0)
            for metric in metrics
        }
        active_config = config or RiskScoringConfig.default()
        result = self.engine.score(
            incident, summary, metric_values, tuple(links), tuple(suppliers), active_config
        )
        return await self.repository.save(
            incident_id, getattr(impact, "id", None), active_config.model_version, result
        )

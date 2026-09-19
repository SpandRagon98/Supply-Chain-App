"""Application service for persisting deterministic impact assessments."""

from uuid import UUID

from app.core.errors import NotFoundError
from app.impact import ImpactCalculator, ImpactResult
from app.repositories.impact import ImpactRepository


class ImpactService:
    def __init__(
        self, repository: ImpactRepository, calculator: ImpactCalculator | None = None
    ) -> None:
        self.repository, self.calculator = repository, calculator or ImpactCalculator()

    async def assess(self, incident_id: UUID) -> tuple[object, ImpactResult]:
        snapshot = await self.repository.snapshot(incident_id)
        if snapshot is None:
            raise NotFoundError("Disruption incident was not found")
        result = self.calculator.calculate(snapshot)
        assessment = await self.repository.save(
            incident_id, result.summary, result.metrics, self.calculator.calculation_version
        )
        return assessment, result

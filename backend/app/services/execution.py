"""Idempotent action persistence, mock execution, and lifecycle verification."""

from datetime import UTC, datetime
from time import perf_counter

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import ExecutionStatus, IncidentStatus, VerificationStatus
from app.domain.models import (
    DisruptionIncident,
    ExecutionAction,
    ExecutionResult,
    Recommendation,
    VerificationResult,
)
from app.domain.tenant import TenantContext
from app.execution.adapters import ExecutionAdapter, VerificationEvaluator


class ExecutionService:
    def __init__(
        self, session: AsyncSession, tenant: TenantContext, adapters: dict[str, ExecutionAdapter]
    ) -> None:
        self.session, self.tenant, self.adapters = session, tenant, adapters

    async def execute(
        self,
        recommendation: Recommendation,
        action_type: str,
        adapter_key: str,
        parameters: dict[str, object],
        idempotency_key: str,
    ) -> ExecutionAction:
        existing = (
            await self.session.scalars(
                select(ExecutionAction).where(
                    ExecutionAction.organization_id == self.tenant.organization_id,
                    ExecutionAction.idempotency_key == idempotency_key,
                )
            )
        ).first()
        if existing is not None:
            return existing
        adapter = self.adapters.get(adapter_key)
        if adapter is None:
            raise ValueError(f"Unknown execution adapter: {adapter_key}")
        action = ExecutionAction(
            organization_id=self.tenant.organization_id,
            recommendation_id=recommendation.id,
            action_type=action_type,
            adapter_key=adapter_key,
            idempotency_key=idempotency_key,
            status=ExecutionStatus.RUNNING,
            parameters=parameters,
            attempt_count=1,
            started_at=datetime.now(UTC),
        )
        self.session.add(action)
        await self.session.flush()
        started = perf_counter()
        try:
            response = await adapter.execute(action_type, parameters, idempotency_key)
            action.status, action.completed_at = response.status, datetime.now(UTC)
            result = ExecutionResult(
                organization_id=self.tenant.organization_id,
                execution_action_id=action.id,
                attempt_number=1,
                status=response.status,
                external_reference=response.external_reference,
                response_payload=response.payload,
                duration_ms=int((perf_counter() - started) * 1000),
            )
        except Exception as error:
            action.status, action.completed_at = ExecutionStatus.FAILED, datetime.now(UTC)
            result = ExecutionResult(
                organization_id=self.tenant.organization_id,
                execution_action_id=action.id,
                attempt_number=1,
                status=ExecutionStatus.FAILED,
                error_code=type(error).__name__,
                error_message="Adapter execution failed.",
                duration_ms=int((perf_counter() - started) * 1000),
            )
        self.session.add(result)
        await self.session.flush()
        return action


class VerificationService:
    def __init__(
        self,
        session: AsyncSession,
        tenant: TenantContext,
        evaluator: VerificationEvaluator | None = None,
    ) -> None:
        self.session, self.tenant, self.evaluator = (
            session,
            tenant,
            evaluator or VerificationEvaluator(),
        )

    async def verify(
        self,
        incident: DisruptionIncident,
        recommendation: Recommendation,
        actual_outcome: dict[str, object],
    ) -> VerificationResult:
        predicted = recommendation.structured_summary
        status, variance = self.evaluator.evaluate(predicted, actual_outcome)
        result = VerificationResult(
            organization_id=self.tenant.organization_id,
            incident_id=incident.id,
            recommendation_id=recommendation.id,
            status=status,
            verified_at=datetime.now(UTC),
            predicted_outcome=predicted,
            actual_outcome=actual_outcome,
            variance=variance,
        )
        if status is VerificationStatus.RESOLVED:
            incident.status = IncidentStatus.RESOLVED
        elif status is VerificationStatus.REQUIRES_NEW_MITIGATION:
            incident.status = IncidentStatus.MITIGATION_PROPOSED
        else:
            incident.status = IncidentStatus.MONITORING
        self.session.add(result)
        await self.session.flush()
        return result

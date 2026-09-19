"""Mock-safe action adapter and deterministic predicted-versus-actual evaluation."""

from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha256
from typing import Protocol

from app.domain.enums import ExecutionStatus, VerificationStatus


@dataclass(frozen=True, slots=True)
class AdapterResult:
    status: ExecutionStatus
    external_reference: str
    payload: dict[str, object]


class ExecutionAdapter(Protocol):
    key: str

    async def execute(
        self, action_type: str, parameters: dict[str, object], idempotency_key: str
    ) -> AdapterResult: ...


class MockExecutionAdapter:
    """Deterministic development adapter with stable external references per idempotency key."""

    key = "mock-erp"

    async def execute(
        self, action_type: str, parameters: dict[str, object], idempotency_key: str
    ) -> AdapterResult:
        reference = (
            "MOCK-" + sha256(f"{action_type}:{idempotency_key}".encode()).hexdigest()[:16].upper()
        )
        return AdapterResult(
            ExecutionStatus.SUCCEEDED,
            reference,
            {
                "adapter": self.key,
                "action_type": action_type,
                "parameters": parameters,
                "simulated": True,
            },
        )


class VerificationEvaluator:
    """Evaluates actual protected revenue against the deterministic predicted outcome."""

    def evaluate(
        self, predicted: dict[str, object], actual: dict[str, object]
    ) -> tuple[VerificationStatus, dict[str, object]]:
        predicted_revenue = Decimal(str(predicted.get("revenue_protected", 0)))
        actual_revenue = Decimal(str(actual.get("revenue_protected", 0)))
        variance = actual_revenue - predicted_revenue
        if predicted_revenue == 0:
            status = (
                VerificationStatus.RESOLVED
                if actual_revenue >= 0
                else VerificationStatus.REQUIRES_NEW_MITIGATION
            )
        elif actual_revenue >= predicted_revenue * Decimal(".9"):
            status = VerificationStatus.RESOLVED
        elif actual_revenue > 0:
            status = VerificationStatus.PARTIALLY_RESOLVED
        else:
            status = VerificationStatus.REQUIRES_NEW_MITIGATION
        return status, {
            "revenue_protected": str(variance),
            "predicted_revenue_protected": str(predicted_revenue),
            "actual_revenue_protected": str(actual_revenue),
        }

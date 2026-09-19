"""Phase 12 idempotent mock execution and deterministic verification tests."""

from decimal import Decimal

import pytest

from app.domain.enums import ExecutionStatus, VerificationStatus
from app.execution import MockExecutionAdapter, VerificationEvaluator


async def test_mock_adapter_is_stable_for_the_same_idempotency_key() -> None:
    adapter = MockExecutionAdapter()
    first = await adapter.execute("EXPEDITE", {"quantity": 10}, "incident-1:expedite")
    second = await adapter.execute("EXPEDITE", {"quantity": 10}, "incident-1:expedite")
    assert first.status is ExecutionStatus.SUCCEEDED
    assert first.external_reference == second.external_reference


@pytest.mark.parametrize(
    ("actual", "status"),
    [
        ("950", VerificationStatus.RESOLVED),
        ("400", VerificationStatus.PARTIALLY_RESOLVED),
        ("0", VerificationStatus.REQUIRES_NEW_MITIGATION),
    ],
)
def test_verification_evaluates_predicted_against_actual_outcome(
    actual: str, status: VerificationStatus
) -> None:
    result, variance = VerificationEvaluator().evaluate(
        {"revenue_protected": Decimal("1000")}, {"revenue_protected": Decimal(actual)}
    )
    assert result is status
    assert "revenue_protected" in variance

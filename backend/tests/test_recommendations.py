"""Phase 11 deterministic recommendation and approval routing tests."""

from decimal import Decimal

import pytest

from app.domain.enums import RoleKey
from app.recommendations import ApprovalRouter, RecommendationEngine
from app.recommendations.engine import ScenarioSummary


def scenario(identifier: str, score: str | None, revenue: str = "1000") -> ScenarioSummary:
    return ScenarioSummary(
        identifier,
        identifier,
        Decimal("100"),
        Decimal("3"),
        Decimal(revenue),
        4,
        Decimal(".9"),
        Decimal(score) if score else None,
    )


def test_recommendation_preserves_numerical_explanation_and_alternatives() -> None:
    result = RecommendationEngine().recommend(
        (scenario("wait", None), scenario("alternate", ".8", "9000"), scenario("expedite", ".7")),
        Decimal("70"),
    )
    assert result.selected.id == "alternate"
    assert result.confidence == Decimal(".76000")
    assert result.structured_summary["orders_protected"] == 4
    assert {item.id for item in result.alternatives} == {"wait", "expedite"}


def test_approval_router_routes_amounts_and_escalates_new_suppliers() -> None:
    router = ApprovalRouter.default()
    assert router.route(Decimal("9999")).required_role is RoleKey.PROCUREMENT
    assert router.route(Decimal("10000")).required_role is RoleKey.SUPPLY_CHAIN_MANAGER
    assert (
        router.route(Decimal("500"), new_supplier=True).required_role
        is RoleKey.SUPPLY_CHAIN_MANAGER
    )
    with pytest.raises(ValueError):
        router.route(Decimal("-1"))

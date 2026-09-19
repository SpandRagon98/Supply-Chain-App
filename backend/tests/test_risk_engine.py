"""Phase 8 configurable risk-engine tests."""

from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.domain.enums import Severity
from app.risk import RiskEngine, RiskScoringConfig


def test_risk_engine_scores_and_explains_each_factor() -> None:
    supplier_id, material_id = uuid4(), uuid4()
    incident = SimpleNamespace(id=uuid4(), severity=Severity.CRITICAL, confidence=Decimal(".9"))
    result = RiskEngine().score(
        incident,
        {
            "affected_material_ids": [str(material_id)],
            "inventory_coverage": [{"days_of_supply": "2"}],
        },
        {"revenue_at_risk": Decimal("5000000")},
        (SimpleNamespace(material_id=material_id, supplier_id=supplier_id),),
        (SimpleNamespace(id=supplier_id, criticality=90),),
    )
    assert result.score == Decimal("89.857")
    assert result.band.value == "CRITICAL"
    assert {factor.key for factor in result.factors} == {
        "severity",
        "confidence",
        "supplier_criticality",
        "single_source_dependency",
        "inventory_exposure",
        "revenue_exposure",
    }
    assert "severity" in result.explanation


def test_risk_configuration_requires_complete_normalized_weights() -> None:
    with pytest.raises(ValueError, match="sum exactly"):
        RiskScoringConfig.from_mapping(
            {"weights": {key: Decimal(".1") for key in RiskScoringConfig.default().weights}}
        )

"""Phase 9 OR-Tools optimizer tests."""

from decimal import Decimal

from app.optimization import OptimizationObjective, ScenarioCandidate, ScenarioOptimizer


def test_optimizer_selects_the_best_scenario_for_each_objective() -> None:
    candidates = (
        ScenarioCandidate(
            "wait", Decimal("0"), Decimal("15"), Decimal("0"), Decimal(".1"), Decimal(".9")
        ),
        ScenarioCandidate(
            "expedite", Decimal("120"), Decimal("4"), Decimal("700"), Decimal(".8"), Decimal(".8")
        ),
        ScenarioCandidate(
            "alternate", Decimal("80"), Decimal("6"), Decimal("900"), Decimal(".75"), Decimal(".7")
        ),
    )
    optimizer = ScenarioOptimizer()
    assert optimizer.select(candidates, OptimizationObjective.MIN_COST)[0] == 0
    assert optimizer.select(candidates, OptimizationObjective.MIN_DELAY)[0] == 1
    assert optimizer.select(candidates, OptimizationObjective.MAX_REVENUE_PROTECTED)[0] == 2


def test_optimizer_rejects_an_all_infeasible_plan() -> None:
    candidate = ScenarioCandidate(
        "blocked", Decimal(0), Decimal(0), Decimal(0), Decimal(0), Decimal(0), False
    )
    try:
        ScenarioOptimizer().select((candidate,), OptimizationObjective.BALANCED)
    except ValueError as error:
        assert "feasible" in str(error)
    else:
        raise AssertionError("Expected infeasible scenario selection to fail")

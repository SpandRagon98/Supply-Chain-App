"""Feasible mitigation alternatives and a small transparent MIP selection model."""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from ortools.linear_solver import pywraplp


class OptimizationObjective(StrEnum):
    MIN_COST = "MIN_COST"
    MIN_DELAY = "MIN_DELAY"
    MAX_REVENUE_PROTECTED = "MAX_REVENUE_PROTECTED"
    MAX_SERVICE_LEVEL = "MAX_SERVICE_LEVEL"
    MAX_RESILIENCE = "MAX_RESILIENCE"
    BALANCED = "BALANCED"


@dataclass(frozen=True, slots=True)
class ScenarioCandidate:
    name: str
    incremental_cost: Decimal
    delay_days: Decimal
    revenue_protected: Decimal
    expected_service_level: Decimal
    feasibility_score: Decimal
    feasible: bool = True


class ScenarioOptimizer:
    """Select one feasible scenario using OR-Tools, preserving each objective coefficient."""

    def select(
        self, candidates: tuple[ScenarioCandidate, ...], objective: OptimizationObjective
    ) -> tuple[int, Decimal]:
        feasible = [
            (index, candidate) for index, candidate in enumerate(candidates) if candidate.feasible
        ]
        if not feasible:
            raise ValueError("At least one feasible mitigation scenario is required")
        solver = pywraplp.Solver.CreateSolver("CBC_MIXED_INTEGER_PROGRAMMING")
        if solver is None:
            raise RuntimeError("OR-Tools CBC solver is unavailable")
        variables = {index: solver.BoolVar(f"scenario_{index}") for index, _ in feasible}
        solver.Add(sum(variables.values()) == 1)
        values = {
            index: self._value(candidate, objective, tuple(candidate for _, candidate in feasible))
            for index, candidate in feasible
        }
        objective_fn = solver.Objective()
        for index, value in values.items():
            objective_fn.SetCoefficient(variables[index], float(value))
        objective_fn.SetMaximization()
        if solver.Solve() != pywraplp.Solver.OPTIMAL:
            raise RuntimeError("OR-Tools could not select a mitigation scenario")
        selected = next(index for index in variables if variables[index].solution_value() > 0.5)
        return selected, values[selected]

    def _value(
        self,
        candidate: ScenarioCandidate,
        objective: OptimizationObjective,
        candidates: tuple[ScenarioCandidate, ...],
    ) -> Decimal:
        if objective is OptimizationObjective.MIN_COST:
            return -candidate.incremental_cost
        if objective is OptimizationObjective.MIN_DELAY:
            return -candidate.delay_days
        if objective is OptimizationObjective.MAX_REVENUE_PROTECTED:
            return candidate.revenue_protected
        if objective is OptimizationObjective.MAX_SERVICE_LEVEL:
            return candidate.expected_service_level
        if objective is OptimizationObjective.MAX_RESILIENCE:
            return candidate.feasibility_score
        max_cost = max(
            (item.incremental_cost for item in candidates), default=Decimal(1)
        ) or Decimal(1)
        max_delay = max((item.delay_days for item in candidates), default=Decimal(1)) or Decimal(1)
        max_revenue = max(
            (item.revenue_protected for item in candidates), default=Decimal(1)
        ) or Decimal(1)
        return (
            candidate.revenue_protected / max_revenue * Decimal(".35")
            + candidate.expected_service_level * Decimal(".25")
            + candidate.feasibility_score * Decimal(".25")
            - candidate.incremental_cost / max_cost * Decimal(".10")
            - candidate.delay_days / max_delay * Decimal(".05")
        )

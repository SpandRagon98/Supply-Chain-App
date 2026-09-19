"""Recommendation selection and approval routing with explicit, inspectable rules."""

from dataclasses import dataclass
from decimal import Decimal

from app.domain.enums import RoleKey


@dataclass(frozen=True, slots=True)
class ScenarioSummary:
    id: str
    name: str
    incremental_cost: Decimal
    delay_days: Decimal
    revenue_protected: Decimal
    orders_protected: int
    feasibility_score: Decimal
    objective_score: Decimal | None
    assumptions: tuple[dict[str, object], ...] = ()
    constraints: tuple[dict[str, object], ...] = ()


@dataclass(frozen=True, slots=True)
class RecommendationResult:
    selected: ScenarioSummary
    alternatives: tuple[ScenarioSummary, ...]
    confidence: Decimal
    rationale: str
    risks: tuple[dict[str, object], ...]
    structured_summary: dict[str, object]


class RecommendationEngine:
    """Turns optimizer output into a durable, numerical, explainable recommendation."""

    def recommend(
        self, scenarios: tuple[ScenarioSummary, ...], risk_score: Decimal | None = None
    ) -> RecommendationResult:
        eligible = [scenario for scenario in scenarios if scenario.objective_score is not None]
        if not eligible:
            raise ValueError("A recommendation requires an optimizer-selected scenario")
        selected = max(
            eligible, key=lambda scenario: scenario.objective_score or Decimal("-Infinity")
        )
        alternatives = tuple(scenario for scenario in scenarios if scenario.id != selected.id)
        risk_penalty = min(max(risk_score or Decimal(0), Decimal(0)), Decimal(100)) / Decimal(500)
        confidence = max(Decimal(0), selected.feasibility_score - risk_penalty).quantize(
            Decimal(".00001")
        )
        risks: tuple[dict[str, object], ...] = tuple(
            {"constraint": constraint} for constraint in selected.constraints
        )
        summary: dict[str, object] = {
            "incremental_cost": str(selected.incremental_cost),
            "delay_days": str(selected.delay_days),
            "revenue_protected": str(selected.revenue_protected),
            "orders_protected": selected.orders_protected,
            "impact_avoided": str(selected.revenue_protected),
            "assumptions": list(selected.assumptions),
            "risk_score": str(risk_score) if risk_score is not None else None,
        }
        rationale = (
            f"{selected.name} is the optimizer-selected feasible option: it protects "
            f"{selected.orders_protected} orders and {selected.revenue_protected} in revenue "
            f"with {selected.delay_days} days expected delay."
        )
        return RecommendationResult(selected, alternatives, confidence, rationale, risks, summary)


@dataclass(frozen=True, slots=True)
class ApprovalPolicy:
    maximum_amount: Decimal | None
    required_role: RoleKey
    requires_new_supplier: bool = False


class ApprovalRouter:
    """Routes by ordered monetary bands, with an explicit new-supplier escalation override."""

    def __init__(self, policies: tuple[ApprovalPolicy, ...]) -> None:
        if not policies:
            raise ValueError("At least one approval policy is required")
        self.policies = policies

    @classmethod
    def default(cls) -> "ApprovalRouter":
        return cls(
            (
                ApprovalPolicy(Decimal("10000"), RoleKey.PROCUREMENT),
                ApprovalPolicy(Decimal("100000"), RoleKey.SUPPLY_CHAIN_MANAGER),
                ApprovalPolicy(None, RoleKey.ADMIN),
            )
        )

    def route(self, amount: Decimal, *, new_supplier: bool = False) -> ApprovalPolicy:
        if amount < 0:
            raise ValueError("Approval amount cannot be negative")
        if new_supplier:
            candidates = [policy for policy in self.policies if policy.requires_new_supplier]
            if candidates:
                return candidates[0]
            return ApprovalPolicy(None, RoleKey.SUPPLY_CHAIN_MANAGER, True)
        for policy in self.policies:
            if not policy.requires_new_supplier and (
                policy.maximum_amount is None or amount < policy.maximum_amount
            ):
                return policy
        raise ValueError("Approval policy has no open-ended monetary band")

"""Phase 13 offline end-to-end Taiwan Typhoon workflow validation."""

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from app.connectors.contracts import ConnectorContext
from app.connectors.mocks import MockWeatherAdapter
from app.domain.enums import Severity
from app.domain.models import (
    BillOfMaterial,
    BOMComponent,
    ConsumptionHistory,
    Customer,
    CustomerOrder,
    CustomerOrderLine,
    InventorySnapshot,
    MaterialSupplier,
    PurchaseOrder,
    Shipment,
    Supplier,
    SupplierSite,
)
from app.execution import MockExecutionAdapter, VerificationEvaluator
from app.impact import ImpactCalculator, ImpactSnapshot
from app.intelligence.contracts import EntityCandidate, SignalIntelligenceConfig
from app.intelligence.detection import SignalDetector
from app.intelligence.resolution import EntityResolver
from app.optimization import OptimizationObjective, ScenarioCandidate, ScenarioOptimizer
from app.recommendations import ApprovalRouter, RecommendationEngine
from app.recommendations.engine import ScenarioSummary
from app.risk import RiskEngine
from app.seed.demo import DemoDataset, build_demo_dataset


def from_demo[T](dataset: DemoDataset, model: type[T]) -> tuple[T, ...]:
    return tuple(entity for entity in dataset.entities if isinstance(entity, model))


async def test_taiwan_typhoon_runs_from_signal_through_verified_resolution() -> None:
    dataset = build_demo_dataset()
    suppliers = from_demo(dataset, Supplier)
    sites = from_demo(dataset, SupplierSite)
    weather = await MockWeatherAdapter().fetch(ConnectorContext(uuid4(), uuid4(), uuid4(), {}, {}))
    signal = SignalDetector().detect(weather.records[0], SignalIntelligenceConfig())
    assert signal is not None and signal.severity is Severity.HIGH

    candidates = tuple(
        EntityCandidate("supplier_site", site.id, (("city", site.city),)) for site in sites
    )
    matches = EntityResolver().resolve(
        signal.entity_references, candidates, SignalIntelligenceConfig()
    )
    formosa_site = next(
        site
        for site in sites
        if site.supplier_id
        == next(supplier.id for supplier in suppliers if supplier.code == "FORMOSA")
    )
    assert any(match.entity_id == formosa_site.id for match in matches)

    incident = SimpleNamespace(
        id=uuid4(),
        severity=signal.severity,
        confidence=signal.confidence,
        started_at=datetime.now(UTC),
    )
    snapshot = ImpactSnapshot(
        incident=incident,
        incident_entities=(
            SimpleNamespace(entity_type="supplier_site", entity_id=formosa_site.id),
        ),
        suppliers=suppliers,
        supplier_sites=sites,
        materials=(),
        material_suppliers=from_demo(dataset, MaterialSupplier),
        boms=from_demo(dataset, BillOfMaterial),
        bom_components=from_demo(dataset, BOMComponent),
        inventories=from_demo(dataset, InventorySnapshot),
        consumption=from_demo(dataset, ConsumptionHistory),
        customers=from_demo(dataset, Customer),
        orders=from_demo(dataset, CustomerOrder),
        order_lines=from_demo(dataset, CustomerOrderLine),
        purchase_orders=from_demo(dataset, PurchaseOrder),
        shipments=from_demo(dataset, Shipment),
    )
    impact = ImpactCalculator().calculate(snapshot)
    metric_values = {metric.key: metric.value for metric in impact.metrics}
    assert metric_values["impacted_material_count"] > 0
    assert metric_values["revenue_at_risk"] > 0

    risk = RiskEngine().score(
        incident, impact.summary, metric_values, from_demo(dataset, MaterialSupplier), suppliers
    )
    assert risk.score > 0
    candidates_to_optimize = (
        ScenarioCandidate(
            "wait", Decimal(0), Decimal(14), Decimal(0), Decimal(".1"), Decimal(".95")
        ),
        ScenarioCandidate(
            "expedite",
            Decimal("200000"),
            Decimal(4),
            metric_values["revenue_at_risk"] * Decimal(".7"),
            Decimal(".75"),
            Decimal(".8"),
        ),
        ScenarioCandidate(
            "alternate source",
            Decimal("160000"),
            Decimal(7),
            metric_values["revenue_at_risk"] * Decimal(".85"),
            Decimal(".7"),
            Decimal(".72"),
        ),
    )
    selected_index, objective_score = ScenarioOptimizer().select(
        candidates_to_optimize, OptimizationObjective.MAX_REVENUE_PROTECTED
    )
    scenario_summaries = tuple(
        ScenarioSummary(
            str(index),
            candidate.name,
            candidate.incremental_cost,
            candidate.delay_days,
            candidate.revenue_protected,
            int(metric_values["customer_orders_at_risk"]),
            candidate.feasibility_score,
            objective_score if index == selected_index else None,
        )
        for index, candidate in enumerate(candidates_to_optimize)
    )
    recommendation = RecommendationEngine().recommend(scenario_summaries, risk.score)
    assert recommendation.selected.name == "alternate source"
    assert (
        ApprovalRouter.default().route(recommendation.selected.incremental_cost).required_role.value
        == "ADMIN"
    )

    execution = await MockExecutionAdapter().execute(
        "SWITCH_SUPPLIER", {"scenario": recommendation.selected.id}, f"{incident.id}:switch"
    )
    assert execution.status.value == "SUCCEEDED"
    status, variance = VerificationEvaluator().evaluate(
        recommendation.structured_summary,
        {"revenue_protected": recommendation.selected.revenue_protected},
    )
    assert status.value == "RESOLVED"
    assert Decimal(str(variance["revenue_protected"])) == 0

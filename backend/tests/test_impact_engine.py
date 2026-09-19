"""Phase 7 deterministic impact-analysis tests."""

from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from app.domain.enums import OrderStatus
from app.impact import ImpactCalculator, ImpactSnapshot


def row(**values: object) -> SimpleNamespace:
    values.setdefault("id", uuid4())
    return SimpleNamespace(**values)


def test_impact_traverses_multilevel_bom_and_calculates_exposure() -> None:
    supplier_id, site_id, material_id = uuid4(), uuid4(), uuid4()
    assembly_id, finished_id, facility_id, customer_id = uuid4(), uuid4(), uuid4(), uuid4()
    bom_assembly, bom_finished = uuid4(), uuid4()
    order_id = uuid4()
    snapshot = ImpactSnapshot(
        incident=row(),
        incident_entities=(row(entity_type="supplier", entity_id=supplier_id),),
        suppliers=(),
        supplier_sites=(row(supplier_id=supplier_id),),
        materials=(),
        material_suppliers=(row(material_id=material_id, supplier_id=supplier_id),),
        boms=(
            row(id=bom_assembly, product_id=assembly_id, is_active=True),
            row(id=bom_finished, product_id=finished_id, is_active=True),
        ),
        bom_components=(
            row(
                bill_of_material_id=bom_assembly, material_id=material_id, component_product_id=None
            ),
            row(
                bill_of_material_id=bom_finished, material_id=None, component_product_id=assembly_id
            ),
        ),
        inventories=(
            row(
                facility_id=facility_id,
                material_id=material_id,
                on_hand_quantity=Decimal("120"),
                allocated_quantity=Decimal("20"),
                captured_at=datetime(2026, 9, 1, tzinfo=UTC),
            ),
        ),
        consumption=(
            row(
                facility_id=facility_id,
                material_id=material_id,
                quantity=Decimal("70"),
                period_start=date(2026, 8, 25),
                period_end=date(2026, 8, 31),
            ),
        ),
        customers=(row(id=customer_id, priority=95),),
        orders=(
            row(
                id=order_id,
                customer_id=customer_id,
                fulfillment_facility_id=facility_id,
                status=OrderStatus.OPEN,
                currency="INR",
            ),
        ),
        order_lines=(
            row(
                customer_order_id=order_id,
                product_id=finished_id,
                ordered_quantity=Decimal("3"),
                fulfilled_quantity=Decimal("1"),
                unit_price=Decimal("100"),
            ),
        ),
        purchase_orders=(row(supplier_id=supplier_id, supplier_site_id=site_id),),
        shipments=(row(supplier_id=supplier_id, origin_supplier_site_id=site_id),),
    )

    result = ImpactCalculator().calculate(snapshot)
    metrics = {metric.key: metric.value for metric in result.metrics}
    assert result.impacted_product_ids == {assembly_id, finished_id}
    assert metrics["impacted_material_count"] == 1
    assert metrics["customer_orders_at_risk"] == 1
    assert metrics["priority_customer_orders_at_risk"] == 1
    assert metrics["revenue_at_risk"] == Decimal("200")
    assert metrics["minimum_days_of_supply"] == Decimal("10")
    assert result.summary["earliest_projected_stockout_at"] == "2026-09-11T00:00:00+00:00"


def test_impact_with_no_resolved_entities_has_zero_exposure() -> None:
    snapshot = ImpactSnapshot(row(), (), (), (), (), (), (), (), (), (), (), (), (), (), ())
    result = ImpactCalculator().calculate(snapshot)
    assert result.impacted_material_ids == set()
    assert {metric.key: metric.value for metric in result.metrics}["revenue_at_risk"] == 0

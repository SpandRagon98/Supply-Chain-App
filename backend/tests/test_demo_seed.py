"""Phase 3 Nova Electronics demo-data contract tests."""

import os
from collections import Counter
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.domain.base import TenantEntity
from app.domain.models import (
    BOMComponent,
    CustomerOrder,
    InventorySnapshot,
    Material,
    MaterialSupplier,
    Organization,
    Product,
    PurchaseOrder,
    Shipment,
    Supplier,
    SupplierSite,
)
from app.seed.demo import build_demo_dataset, demo_id, seed_demo_data


def entities_of_type[T](entity_type: type[T]) -> tuple[T, ...]:
    return tuple(
        entity for entity in build_demo_dataset().entities if isinstance(entity, entity_type)
    )


def test_demo_dataset_has_stable_comprehensive_counts() -> None:
    dataset = build_demo_dataset()

    assert len(dataset.entities) == 944
    assert dataset.counts == {
        "ApprovalRequest": 1,
        "AuditLog": 1,
        "BOMComponent": 65,
        "BillOfMaterial": 10,
        "ConsumptionHistory": 120,
        "Connector": 5,
        "Customer": 18,
        "CustomerOrder": 42,
        "CustomerOrderLine": 84,
        "DistributionCenter": 2,
        "DisruptionIncident": 1,
        "ExecutionAction": 1,
        "InventorySnapshot": 176,
        "ImpactAssessment": 1,
        "ImpactMetric": 2,
        "LLMModelConfiguration": 1,
        "Material": 40,
        "MaterialSupplier": 58,
        "Organization": 1,
        "Plant": 3,
        "PromptTemplate": 1,
        "Product": 10,
        "PurchaseOrder": 30,
        "PurchaseOrderLine": 56,
        "Recommendation": 1,
        "RiskAssessment": 1,
        "Role": 7,
        "Shipment": 20,
        "ShipmentEvent": 60,
        "SignalSource": 5,
        "Scenario": 3,
        "ScenarioAction": 3,
        "StageConfiguration": 8,
        "StageDefinition": 8,
        "StageDependency": 7,
        "Supplier": 18,
        "SupplierRating": 36,
        "SupplierSite": 19,
        "User": 7,
        "UserRole": 7,
        "Warehouse": 3,
        "WorkflowDefinition": 1,
        "WorkflowVersion": 1,
    }
    assert len({entity.id for entity in dataset.entities}) == len(dataset.entities)
    assert [entity.id for entity in dataset.entities] == [
        entity.id for entity in build_demo_dataset().entities
    ]


def test_every_tenant_row_belongs_to_nova_electronics() -> None:
    dataset = build_demo_dataset()
    organization = next(entity for entity in dataset.entities if isinstance(entity, Organization))

    assert organization.id == demo_id("organization", "nova-electronics")
    assert organization.slug == "nova-electronics"
    assert all(
        entity.organization_id == organization.id
        for entity in dataset.entities
        if isinstance(entity, TenantEntity)
    )


def test_demo_network_supports_multi_level_and_supplier_disruption_scenarios() -> None:
    suppliers = {supplier.id: supplier for supplier in entities_of_type(Supplier)}
    sites = {site.id: site for site in entities_of_type(SupplierSite)}
    materials = {material.sku: material for material in entities_of_type(Material)}
    products = {product.sku: product for product in entities_of_type(Product)}
    sources = entities_of_type(MaterialSupplier)
    components = entities_of_type(BOMComponent)

    cpu_sources = {
        suppliers[source.supplier_id].code
        for source in sources
        if source.material_id == materials["CPU-X9"].id
    }
    battery_sources = {
        suppliers[source.supplier_id].code
        for source in sources
        if source.material_id == materials["CELL-LI6"].id
    }

    assert cpu_sources == {"FORMOSA", "HANSEONG"}
    assert battery_sources == {"KYOTO-BATT"}
    assert {site.city for site in sites.values()} >= {"Tainan", "Hsinchu", "Singapore"}
    assert any(
        component.component_product_id == products["ASM-MB-PRO"].id for component in components
    )
    assert any(
        component.material_id == materials["CPU-X9"].id and component.is_critical
        for component in components
    )


def test_demo_operations_include_pressure_signals_and_active_flows() -> None:
    materials = {material.id: material for material in entities_of_type(Material)}
    cpu_inventory = [
        snapshot
        for snapshot in entities_of_type(InventorySnapshot)
        if snapshot.material_id is not None and materials[snapshot.material_id].sku == "CPU-X9"
    ]

    assert max(snapshot.on_hand_quantity for snapshot in cpu_inventory) == Decimal("480")
    assert Counter(order.status.value for order in entities_of_type(PurchaseOrder))["OPEN"] > 0
    assert Counter(order.status.value for order in entities_of_type(CustomerOrder))["OPEN"] > 0
    assert Counter(shipment.status.value for shipment in entities_of_type(Shipment))["DELAYED"] > 0


@pytest.mark.asyncio
async def test_postgresql_seed_is_repeatable_when_database_is_available() -> None:
    database_url = os.getenv("TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip("TEST_DATABASE_URL is only configured for the PostgreSQL CI integration test")

    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session, session.begin():
            first = await seed_demo_data(session)
        async with session_factory() as session, session.begin():
            second = await seed_demo_data(session)
        async with session_factory() as session:
            organization_count = await session.scalar(
                select(func.count())
                .select_from(Organization)
                .where(Organization.slug == "nova-electronics")
            )
            supplier_count = await session.scalar(
                select(func.count())
                .select_from(Supplier)
                .where(Supplier.organization_id == first.organization_id)
            )
            order_count = await session.scalar(
                select(func.count())
                .select_from(CustomerOrder)
                .where(CustomerOrder.organization_id == first.organization_id)
            )

        assert first == second
        assert organization_count == 1
        assert supplier_count == 18
        assert order_count == 42
    finally:
        await engine.dispose()

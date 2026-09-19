"""Canonical schema contract tests."""

from uuid import uuid4

from sqlalchemy.dialects.postgresql import JSONB

from app.domain.base import Base
from app.domain.enums import FacilityType, RoleKey
from app.domain.models import (
    BOMComponent,
    DistributionCenter,
    Facility,
    Material,
    Organization,
    Plant,
    StageConfiguration,
    Supplier,
    Warehouse,
)

EXPECTED_TABLES = {
    "approval_decisions",
    "approval_requests",
    "audit_logs",
    "bills_of_material",
    "bom_components",
    "connector_runs",
    "connectors",
    "consumption_history",
    "customer_order_lines",
    "customer_orders",
    "customers",
    "disruption_incidents",
    "execution_actions",
    "execution_results",
    "external_signals",
    "facilities",
    "impact_assessments",
    "impact_metrics",
    "incident_entities",
    "incident_signals",
    "inventory_snapshots",
    "llm_model_configurations",
    "llm_runs",
    "material_suppliers",
    "materials",
    "notifications",
    "organizations",
    "products",
    "prompt_templates",
    "purchase_order_lines",
    "purchase_orders",
    "recommendations",
    "risk_assessments",
    "risk_factors",
    "roles",
    "scenario_actions",
    "scenarios",
    "shipment_events",
    "shipments",
    "signal_sources",
    "stage_configurations",
    "stage_definitions",
    "stage_dependencies",
    "stage_runs",
    "supplier_ratings",
    "supplier_sites",
    "suppliers",
    "user_roles",
    "users",
    "verification_results",
    "workflow_definitions",
    "workflow_runs",
    "workflow_versions",
}


def test_canonical_schema_contains_every_required_table() -> None:
    assert set(Base.metadata.tables) == EXPECTED_TABLES


def test_every_business_table_is_tenant_scoped() -> None:
    for table_name, table in Base.metadata.tables.items():
        if table_name == "organizations":
            continue

        organization_column = table.c.get("organization_id")
        assert organization_column is not None, table_name
        assert organization_column.nullable is False, table_name
        assert any(
            foreign_key.target_fullname == "organizations.id"
            for foreign_key in organization_column.foreign_keys
        ), table_name


def test_workflow_configuration_uses_postgresql_jsonb() -> None:
    assert isinstance(StageConfiguration.__table__.c.configuration.type, JSONB)
    assert isinstance(StageConfiguration.__table__.c.retry_policy.type, JSONB)
    assert isinstance(StageConfiguration.__table__.c.ai_configuration.type, JSONB)


def test_bom_component_supports_material_and_nested_product_links() -> None:
    foreign_key_targets = {
        foreign_key.target_fullname for foreign_key in BOMComponent.__table__.foreign_keys
    }

    assert "materials.id" in foreign_key_targets
    assert "products.id" in foreign_key_targets
    assert "bills_of_material.id" in foreign_key_targets


def test_facility_specializations_share_one_canonical_table() -> None:
    assert Plant.__table__ is Facility.__table__
    assert Warehouse.__table__ is Facility.__table__
    assert DistributionCenter.__table__ is Facility.__table__
    assert Plant.__mapper_args__["polymorphic_identity"] is FacilityType.PLANT


def test_rbac_keys_match_product_contract() -> None:
    assert {role.value for role in RoleKey} == {
        "ADMIN",
        "SUPPLY_CHAIN_MANAGER",
        "SUPPLY_CHAIN_PLANNER",
        "PROCUREMENT",
        "APPROVER",
        "ANALYST",
        "VIEWER",
    }


def test_transient_entities_preserve_explicit_tenant_identity() -> None:
    organization = Organization(name="Nova Electronics", slug="nova-electronics")
    supplier = Supplier(
        organization_id=uuid4(),
        code="SUP-001",
        name="Test Supplier",
        country_code="IN",
    )
    material = Material(
        organization_id=supplier.organization_id,
        sku="MAT-001",
        name="Test Material",
        unit_of_measure="EA",
    )

    assert organization.id is None
    assert supplier.id is None
    assert material.organization_id == supplier.organization_id

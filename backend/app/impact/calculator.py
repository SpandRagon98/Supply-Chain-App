"""Pure, explainable traversal of the supply network and commercial exposure."""
# mypy: ignore-errors
# ruff: noqa: B009

from dataclasses import dataclass
from datetime import timedelta
from decimal import ROUND_CEILING, Decimal
from typing import Protocol
from uuid import UUID

import networkx as nx

from app.domain.enums import OrderStatus


class HasId(Protocol):
    id: UUID


@dataclass(frozen=True, slots=True)
class ImpactSnapshot:
    """Tenant-scoped input rows; the calculator deliberately has no database dependency."""

    incident: HasId
    incident_entities: tuple[object, ...]
    suppliers: tuple[object, ...]
    supplier_sites: tuple[object, ...]
    materials: tuple[object, ...]
    material_suppliers: tuple[object, ...]
    boms: tuple[object, ...]
    bom_components: tuple[object, ...]
    inventories: tuple[object, ...]
    consumption: tuple[object, ...]
    customers: tuple[object, ...]
    orders: tuple[object, ...]
    order_lines: tuple[object, ...]
    purchase_orders: tuple[object, ...]
    shipments: tuple[object, ...]


@dataclass(frozen=True, slots=True)
class ComputedMetric:
    key: str
    value: Decimal
    unit: str | None = None
    currency: str | None = None
    lineage: tuple[dict[str, object], ...] = ()


@dataclass(frozen=True, slots=True)
class ImpactResult:
    summary: dict[str, object]
    metrics: tuple[ComputedMetric, ...]
    impacted_material_ids: frozenset[UUID]
    impacted_product_ids: frozenset[UUID]


class ImpactCalculator:
    """Computes direct and transitive impact without opaque heuristics or AI."""

    calculation_version = "network-impact-v1"

    def calculate(self, snapshot: ImpactSnapshot) -> ImpactResult:
        entity_ids: dict[str, set[UUID]] = {}
        for entity in snapshot.incident_entities:
            entity_ids.setdefault(str(getattr(entity, "entity_type")), set()).add(
                getattr(entity, "entity_id")
            )
        site_to_supplier = {
            getattr(site, "id"): getattr(site, "supplier_id") for site in snapshot.supplier_sites
        }
        affected_suppliers = set(entity_ids.get("supplier", set()))
        affected_suppliers.update(
            site_to_supplier[value]
            for value in entity_ids.get("supplier_site", set())
            if value in site_to_supplier
        )
        material_ids = set(entity_ids.get("material", set()))
        material_ids.update(
            getattr(link, "material_id")
            for link in snapshot.material_suppliers
            if getattr(link, "supplier_id") in affected_suppliers
        )
        product_ids = self._dependent_products(material_ids, snapshot)
        coverage = self._coverage(material_ids, snapshot)
        order_metrics, order_facilities = self._commercial_exposure(product_ids, snapshot)
        affected_facilities = set(entity_ids.get("facility", set()))
        affected_facilities.update(
            getattr(row, "facility_id")
            for row in snapshot.inventories
            if getattr(row, "material_id", None) in material_ids
        )
        affected_facilities.update(order_facilities)
        affected_shipments = set(entity_ids.get("shipment", set()))
        affected_shipments.update(
            getattr(shipment, "id")
            for shipment in snapshot.shipments
            if getattr(shipment, "supplier_id", None) in affected_suppliers
            or getattr(shipment, "origin_supplier_site_id", None)
            in entity_ids.get("supplier_site", set())
        )
        affected_pos = [
            order
            for order in snapshot.purchase_orders
            if getattr(order, "supplier_id") in affected_suppliers
            or getattr(order, "supplier_site_id", None) in entity_ids.get("supplier_site", set())
        ]
        stockout_dates = [
            row["projected_stockout_at"] for row in coverage if row["projected_stockout_at"]
        ]
        metrics = [
            ComputedMetric("impacted_material_count", Decimal(len(material_ids)), "materials"),
            ComputedMetric("impacted_product_count", Decimal(len(product_ids)), "products"),
            ComputedMetric(
                "impacted_facility_count", Decimal(len(affected_facilities)), "facilities"
            ),
            ComputedMetric(
                "impacted_shipment_count", Decimal(len(affected_shipments)), "shipments"
            ),
            ComputedMetric("impacted_purchase_order_count", Decimal(len(affected_pos)), "orders"),
            *order_metrics,
        ]
        if coverage:
            metrics.append(
                ComputedMetric(
                    "minimum_days_of_supply",
                    min(row["days_of_supply"] for row in coverage),
                    "days",
                    lineage=tuple(self._coverage_lineage(row) for row in coverage),
                )
            )
        summary: dict[str, object] = {
            "calculation_version": self.calculation_version,
            "affected_supplier_ids": sorted(str(value) for value in affected_suppliers),
            "affected_material_ids": sorted(str(value) for value in material_ids),
            "affected_product_ids": sorted(str(value) for value in product_ids),
            "affected_facility_ids": sorted(str(value) for value in affected_facilities),
            "inventory_coverage": [self._json_coverage(row) for row in coverage],
            "earliest_projected_stockout_at": min(stockout_dates).isoformat()
            if stockout_dates
            else None,
        }
        return ImpactResult(
            summary, tuple(metrics), frozenset(material_ids), frozenset(product_ids)
        )

    def _dependent_products(self, material_ids: set[UUID], snapshot: ImpactSnapshot) -> set[UUID]:
        bom_to_product = {
            getattr(bom, "id"): getattr(bom, "product_id")
            for bom in snapshot.boms
            if getattr(bom, "is_active", True)
        }
        graph = nx.DiGraph()
        for component in snapshot.bom_components:
            parent = bom_to_product.get(getattr(component, "bill_of_material_id"))
            child = getattr(component, "component_product_id", None)
            if parent is not None and child is not None:
                graph.add_edge(child, parent)
        impacted: set[UUID] = set()
        direct_parents = {
            bom_to_product.get(getattr(component, "bill_of_material_id"))
            for component in snapshot.bom_components
            if getattr(component, "material_id", None) in material_ids
        }
        for parent in direct_parents - {None}:
            impacted.add(parent)
            impacted.update(nx.descendants(graph, parent))
        return impacted

    def _coverage(
        self, material_ids: set[UUID], snapshot: ImpactSnapshot
    ) -> list[dict[str, object]]:
        result: list[dict[str, object]] = []
        for inventory in snapshot.inventories:
            material_id, facility_id = (
                getattr(inventory, "material_id", None),
                getattr(inventory, "facility_id"),
            )
            if material_id not in material_ids:
                continue
            daily = Decimal(0)
            for history in snapshot.consumption:
                if (
                    getattr(history, "material_id", None) == material_id
                    and getattr(history, "facility_id") == facility_id
                ):
                    days = max(
                        (getattr(history, "period_end") - getattr(history, "period_start")).days
                        + 1,
                        1,
                    )
                    daily += Decimal(getattr(history, "quantity")) / Decimal(days)
            available = max(
                Decimal(getattr(inventory, "on_hand_quantity"))
                - Decimal(getattr(inventory, "allocated_quantity")),
                Decimal(0),
            )
            days_of_supply = available / daily if daily else Decimal("999999")
            stockout = (
                getattr(inventory, "captured_at")
                + timedelta(days=int(days_of_supply.to_integral_value(rounding=ROUND_CEILING)))
                if daily
                else None
            )
            result.append(
                {
                    "material_id": material_id,
                    "facility_id": facility_id,
                    "available_quantity": available,
                    "daily_consumption": daily,
                    "days_of_supply": days_of_supply,
                    "projected_stockout_at": stockout,
                    "inventory_id": getattr(inventory, "id"),
                }
            )
        return result

    def _commercial_exposure(
        self, product_ids: set[UUID], snapshot: ImpactSnapshot
    ) -> tuple[list[ComputedMetric], set[UUID]]:
        orders = {
            getattr(order, "id"): order
            for order in snapshot.orders
            if getattr(order, "status") in {OrderStatus.OPEN, OrderStatus.PARTIALLY_FULFILLED}
        }
        customers = {getattr(customer, "id"): customer for customer in snapshot.customers}
        revenue, quantity = Decimal(0), Decimal(0)
        order_ids: set[UUID] = set()
        priority_order_ids: set[UUID] = set()
        facilities: set[UUID] = set()
        lineage: list[dict[str, object]] = []
        for line in snapshot.order_lines:
            order = orders.get(getattr(line, "customer_order_id"))
            if order is None or getattr(line, "product_id") not in product_ids:
                continue
            remaining = max(
                Decimal(getattr(line, "ordered_quantity"))
                - Decimal(getattr(line, "fulfilled_quantity")),
                Decimal(0),
            )
            if not remaining:
                continue
            amount = remaining * Decimal(getattr(line, "unit_price"))
            quantity += remaining
            revenue += amount
            order_ids.add(getattr(order, "id"))
            customer = customers.get(getattr(order, "customer_id"))
            if customer is not None and getattr(customer, "priority") >= 85:
                priority_order_ids.add(getattr(order, "id"))
            if getattr(order, "fulfillment_facility_id", None):
                facilities.add(getattr(order, "fulfillment_facility_id"))
            lineage.append(
                {
                    "order_id": str(getattr(order, "id")),
                    "order_line_id": str(getattr(line, "id")),
                    "remaining_quantity": str(remaining),
                    "revenue": str(amount),
                }
            )
        currency = next((getattr(order, "currency") for order in orders.values()), None)
        return (
            [
                ComputedMetric(
                    "customer_orders_at_risk",
                    Decimal(len(order_ids)),
                    "orders",
                    lineage=tuple(lineage),
                ),
                ComputedMetric(
                    "priority_customer_orders_at_risk", Decimal(len(priority_order_ids)), "orders"
                ),
                ComputedMetric("quantity_at_risk", quantity, "EA", lineage=tuple(lineage)),
                ComputedMetric(
                    "revenue_at_risk", revenue, currency=currency, lineage=tuple(lineage)
                ),
            ],
            facilities,
        )

    @staticmethod
    def _coverage_lineage(row: dict[str, object]) -> dict[str, object]:
        return {
            "inventory_id": str(row["inventory_id"]),
            "material_id": str(row["material_id"]),
            "facility_id": str(row["facility_id"]),
            "available_quantity": str(row["available_quantity"]),
            "daily_consumption": str(row["daily_consumption"]),
        }

    def _json_coverage(self, row: dict[str, object]) -> dict[str, object]:
        payload = self._coverage_lineage(row)
        payload["days_of_supply"] = str(row["days_of_supply"])
        payload["projected_stockout_at"] = (
            row["projected_stockout_at"].isoformat() if row["projected_stockout_at"] else None
        )
        return payload

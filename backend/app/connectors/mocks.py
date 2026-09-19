"""Deterministic mock adapters for a complete offline demonstration."""

from datetime import UTC, datetime

from app.connectors.contracts import ConnectorBatch, ConnectorContext, ConnectorRecord
from app.connectors.registry import ConnectorRegistry

OBSERVED_AT = datetime(2026, 9, 19, 6, 0, tzinfo=UTC)


def _record(
    adapter: str,
    external_id: str,
    record_type: str,
    payload: dict[str, object],
) -> ConnectorRecord:
    return ConnectorRecord(
        external_id=external_id,
        record_type=record_type,
        observed_at=OBSERVED_AT,
        payload=payload,
        source_uri=f"mock://{adapter}/{external_id}",
        metadata={"mode": "mock", "fixture_version": "2026-09-19"},
    )


def _batch(context: ConnectorContext, records: tuple[ConnectorRecord, ...]) -> ConnectorBatch:
    previous_cursor = context.checkpoint.get("cursor", 0)
    cursor = previous_cursor if isinstance(previous_cursor, int) else 0
    return ConnectorBatch(
        records=records,
        next_checkpoint={"cursor": cursor + len(records), "observed_at": OBSERVED_AT.isoformat()},
        metadata={"mode": "mock", "record_count": len(records)},
    )


class MockERPAdapter:
    key = "mock.erp"
    version = "1.0"

    async def fetch(self, context: ConnectorContext) -> ConnectorBatch:
        return _batch(
            context,
            (
                _record(
                    self.key,
                    "ERP-INV-CPU-X9-PUNE-20260919",
                    "inventory_snapshot",
                    {
                        "material_sku": "CPU-X9",
                        "facility_code": "PUNE-PLANT",
                        "on_hand": 190,
                        "allocated": 42,
                        "unit": "EA",
                    },
                ),
                _record(
                    self.key,
                    "ERP-PO-NOVA-10001",
                    "purchase_order",
                    {
                        "order_number": "PO-NOVA-10001",
                        "supplier_code": "FORMOSA",
                        "material_sku": "CPU-X9",
                        "quantity": 800,
                        "status": "OPEN",
                    },
                ),
                _record(
                    self.key,
                    "ERP-INV-CELL-LI6-CHENNAI-20260919",
                    "inventory_snapshot",
                    {
                        "material_sku": "CELL-LI6",
                        "facility_code": "CHENNAI-PLANT",
                        "on_hand": 620,
                        "allocated": 136,
                        "unit": "EA",
                    },
                ),
            ),
        )


class MockWeatherAdapter:
    key = "mock.weather"
    version = "1.0"

    async def fetch(self, context: ConnectorContext) -> ConnectorBatch:
        return _batch(
            context,
            (
                _record(
                    self.key,
                    "WX-TW-TYPHOON-20260919",
                    "weather_event",
                    {
                        "event": "TYPHOON",
                        "severity": "HIGH",
                        "confidence": 0.96,
                        "country_code": "TW",
                        "cities": ["Tainan", "Hsinchu"],
                        "expected_delay_days": 9,
                    },
                ),
                _record(
                    self.key,
                    "WX-TW-WIND-20260919",
                    "weather_observation",
                    {
                        "event": "EXTREME_WIND",
                        "severity": "HIGH",
                        "latitude": 22.9997,
                        "longitude": 120.227,
                        "wind_kph": 168,
                    },
                ),
            ),
        )


class MockNewsAdapter:
    key = "mock.news"
    version = "1.0"

    async def fetch(self, context: ConnectorContext) -> ConnectorBatch:
        return _batch(
            context,
            (
                _record(
                    self.key,
                    "NEWS-SG-PORT-20260919",
                    "news_event",
                    {
                        "headline": "Singapore terminal closure disrupts regional cargo",
                        "category": "PORT_CLOSURE",
                        "severity": "HIGH",
                        "confidence": 0.91,
                        "location": "Singapore",
                    },
                ),
                _record(
                    self.key,
                    "NEWS-RUMOR-KYOTO-20260919",
                    "news_event",
                    {
                        "headline": "Unverified social report mentions Kyoto battery slowdown",
                        "category": "SUPPLIER_SHUTDOWN",
                        "severity": "MEDIUM",
                        "confidence": 0.31,
                        "supplier_hint": "Kyoto Battery Systems",
                    },
                ),
            ),
        )


class MockShipmentAdapter:
    key = "mock.shipment"
    version = "1.0"

    async def fetch(self, context: ConnectorContext) -> ConnectorBatch:
        return _batch(
            context,
            tuple(
                _record(
                    self.key,
                    f"TMS-NOVA-{shipment_number}-DELAY",
                    "shipment_event",
                    {
                        "shipment_number": shipment_number,
                        "event": "DELAY_REPORTED",
                        "location": "Singapore",
                        "delay_days": 6 + index,
                        "reason": "PORT_CLOSURE",
                    },
                )
                for index, shipment_number in enumerate(("50001", "50004", "50007"))
            ),
        )


class MockSupplierAdapter:
    key = "mock.supplier"
    version = "1.0"

    async def fetch(self, context: ConnectorContext) -> ConnectorBatch:
        return _batch(
            context,
            (
                _record(
                    self.key,
                    "SUP-KYOTO-SHUTDOWN-20260919",
                    "supplier_event",
                    {
                        "supplier_code": "KYOTO-BATT",
                        "site_code": "KYOTO-BATT-01",
                        "event": "PLANT_SHUTDOWN",
                        "severity": "CRITICAL",
                        "confidence": 1.0,
                        "expected_delay_days": 18,
                        "affected_materials": ["CELL-LI6"],
                    },
                ),
                _record(
                    self.key,
                    "SUP-FORMOSA-CAPACITY-20260919",
                    "supplier_capacity",
                    {
                        "supplier_code": "FORMOSA",
                        "material_sku": "CPU-X9",
                        "available_capacity": 2100,
                        "allocated_capacity": 1950,
                        "unit": "EA",
                    },
                ),
            ),
        )


def build_mock_connector_registry() -> ConnectorRegistry:
    registry = ConnectorRegistry()
    registry.register(MockERPAdapter())
    registry.register(MockWeatherAdapter())
    registry.register(MockNewsAdapter())
    registry.register(MockShipmentAdapter())
    registry.register(MockSupplierAdapter())
    return registry

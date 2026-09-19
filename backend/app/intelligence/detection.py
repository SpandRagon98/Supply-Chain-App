"""Deterministic conversion of connector records into canonical signals."""

from decimal import Decimal

from app.connectors.contracts import ConnectorRecord
from app.domain.enums import Severity, SignalCategory
from app.intelligence.contracts import (
    EntityReference,
    NormalizedSignal,
    SignalIntelligenceConfig,
)
from app.intelligence.normalization import (
    normalize_datetime,
    normalize_decimal,
    normalize_identifier,
    normalize_payload,
    normalize_text,
)

SEVERITY_RANK = {
    Severity.INFORMATIONAL: 0,
    Severity.LOW: 1,
    Severity.MEDIUM: 2,
    Severity.HIGH: 3,
    Severity.CRITICAL: 4,
}


class SignalDetector:
    """Classify supported structured records without using an LLM."""

    def detect(
        self,
        record: ConnectorRecord,
        config: SignalIntelligenceConfig,
    ) -> NormalizedSignal | None:
        payload = normalize_payload(record.payload)
        classification = self._classify(record.record_type, payload, config)
        if classification is None:
            return None
        category, default_severity, default_confidence, metadata = classification
        severity = self._severity(payload.get("severity"), default_severity)
        confidence = self._confidence(payload.get("confidence"), default_confidence)
        if confidence < config.minimum_signal_confidence:
            return None

        location = self._location(payload)
        references = self._entity_references(payload)
        title = self._title(record.record_type, payload, category)
        description_value = payload.get("description") or payload.get("headline")
        description = normalize_text(description_value) if description_value else None
        return NormalizedSignal(
            external_id=record.external_id,
            occurred_at=normalize_datetime(payload.get("occurred_at"), fallback=record.observed_at),
            category=category,
            severity=severity,
            confidence=confidence,
            title=title[:240],
            description=description,
            location=location,
            entity_references=references,
            raw_reference=record.source_uri,
            raw_payload=dict(record.payload),
            normalized_payload=payload,
            detection_metadata=metadata,
        )

    def _classify(
        self,
        record_type: str,
        payload: dict[str, object],
        config: SignalIntelligenceConfig,
    ) -> tuple[SignalCategory, Severity, Decimal, dict[str, object]] | None:
        if record_type in {"weather_event", "weather_observation"}:
            return (
                SignalCategory.WEATHER_DISRUPTION,
                Severity.HIGH,
                Decimal("0.90"),
                {"rule": "weather_event"},
            )
        if record_type == "news_event":
            category = self._category(payload.get("category"))
            if category is None:
                return None
            return category, Severity.MEDIUM, Decimal("0.60"), {"rule": "news_category"}
        if record_type == "shipment_event":
            category = (
                SignalCategory.PORT_CLOSURE
                if normalize_identifier(payload.get("reason", "")) == "PORT_CLOSURE"
                else SignalCategory.TRANSPORT_DISRUPTION
            )
            return category, Severity.HIGH, Decimal("0.92"), {"rule": "shipment_delay"}
        if record_type == "supplier_event":
            event = normalize_identifier(payload.get("event", ""))
            category = (
                SignalCategory.SUPPLIER_SHUTDOWN
                if "SHUTDOWN" in event
                else SignalCategory.SUPPLIER_DELAY
            )
            return category, Severity.HIGH, Decimal("0.95"), {"rule": "supplier_event"}
        if record_type == "supplier_capacity":
            available = normalize_decimal(payload.get("available_capacity"))
            allocated = normalize_decimal(payload.get("allocated_capacity"))
            utilization = allocated / available if available > 0 else Decimal("0")
            if utilization < config.capacity_utilization_threshold:
                return None
            severity = Severity.CRITICAL if utilization >= Decimal("1") else Severity.HIGH
            return (
                SignalCategory.CAPACITY_PROBLEM,
                severity,
                Decimal("0.94"),
                {"rule": "capacity_utilization", "utilization": str(utilization)},
            )
        if record_type == "inventory_snapshot":
            on_hand = normalize_decimal(payload.get("on_hand"))
            if on_hand > config.inventory_on_hand_threshold:
                return None
            return (
                SignalCategory.INVENTORY_ANOMALY,
                Severity.HIGH,
                Decimal("0.95"),
                {"rule": "inventory_threshold", "on_hand": str(on_hand)},
            )
        if (
            record_type == "purchase_order"
            and normalize_identifier(payload.get("status", "")) == "LATE"
        ):
            return (
                SignalCategory.LATE_PURCHASE_ORDER,
                Severity.MEDIUM,
                Decimal("0.98"),
                {"rule": "late_purchase_order"},
            )
        if record_type == "manual_disruption":
            category = self._category(payload.get("category")) or SignalCategory.MANUAL_DISRUPTION
            return category, Severity.MEDIUM, Decimal("1"), {"rule": "manual"}
        return None

    @staticmethod
    def _category(value: object) -> SignalCategory | None:
        try:
            return SignalCategory(normalize_identifier(value))
        except ValueError:
            return None

    @staticmethod
    def _severity(value: object, default: Severity) -> Severity:
        if value is None:
            return default
        try:
            return Severity(normalize_identifier(value))
        except ValueError:
            return default

    @staticmethod
    def _confidence(value: object, default: Decimal) -> Decimal:
        confidence = normalize_decimal(value, default=default)
        return max(Decimal("0"), min(Decimal("1"), confidence))

    @staticmethod
    def _location(payload: dict[str, object]) -> dict[str, object]:
        location: dict[str, object] = {}
        for key in ("country_code", "location", "latitude", "longitude", "cities"):
            if key in payload:
                location[key] = payload[key]
        return location

    @staticmethod
    def _entity_references(payload: dict[str, object]) -> tuple[EntityReference, ...]:
        references: list[EntityReference] = []
        mappings = (
            ("supplier_code", "supplier", "code"),
            ("supplier_hint", "supplier", "name"),
            ("site_code", "supplier_site", "code"),
            ("material_sku", "material", "sku"),
            ("facility_code", "facility", "code"),
            ("shipment_number", "shipment", "shipment_number"),
        )
        for key, entity_type, field_name in mappings:
            value = payload.get(key)
            if value:
                references.append(EntityReference(entity_type, normalize_text(value), field_name))
        affected_materials = payload.get("affected_materials")
        if isinstance(affected_materials, list):
            references.extend(
                EntityReference("material", normalize_text(value), "sku")
                for value in affected_materials
                if value
            )
        cities = payload.get("cities")
        if isinstance(cities, list):
            references.extend(
                EntityReference("supplier_site", normalize_text(value), "city")
                for value in cities
                if value
            )
        return tuple(references)

    @staticmethod
    def _title(
        record_type: str,
        payload: dict[str, object],
        category: SignalCategory,
    ) -> str:
        headline = payload.get("headline")
        if headline:
            return normalize_text(headline)
        event = payload.get("event") or payload.get("reason")
        subject = (
            payload.get("supplier_code")
            or payload.get("material_sku")
            or payload.get("shipment_number")
            or payload.get("location")
        )
        pieces = [normalize_text(event)] if event else [category.value.replace("_", " ").title()]
        if subject:
            pieces.append(f"— {normalize_text(subject)}")
        return " ".join(pieces) if pieces else record_type.replace("_", " ").title()

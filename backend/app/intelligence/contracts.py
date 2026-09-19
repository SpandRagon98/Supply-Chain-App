"""Pure data contracts for signal and incident intelligence."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.domain.enums import Severity, SignalCategory


def _decimal_setting(
    values: dict[str, object], key: str, default: str, *, minimum: Decimal, maximum: Decimal
) -> Decimal:
    raw = values.get(key, default)
    try:
        value = Decimal(str(raw))
    except Exception as error:
        raise ValueError(f"{key} must be numeric.") from error
    if value < minimum or value > maximum:
        raise ValueError(f"{key} must be between {minimum} and {maximum}.")
    return value


@dataclass(frozen=True, slots=True)
class SignalIntelligenceConfig:
    minimum_signal_confidence: Decimal = Decimal("0.20")
    auto_incident_confidence: Decimal = Decimal("0.70")
    entity_match_threshold: Decimal = Decimal("0.65")
    entity_review_threshold: Decimal = Decimal("0.85")
    incident_dedup_hours: int = 72
    capacity_utilization_threshold: Decimal = Decimal("0.90")
    inventory_on_hand_threshold: Decimal = Decimal("250")

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> "SignalIntelligenceConfig":
        dedup_raw = values.get("incident_dedup_hours", 72)
        if isinstance(dedup_raw, bool) or not isinstance(dedup_raw, int):
            raise ValueError("incident_dedup_hours must be an integer.")
        if dedup_raw < 1 or dedup_raw > 720:
            raise ValueError("incident_dedup_hours must be between 1 and 720.")
        config = cls(
            minimum_signal_confidence=_decimal_setting(
                values,
                "minimum_signal_confidence",
                "0.20",
                minimum=Decimal("0"),
                maximum=Decimal("1"),
            ),
            auto_incident_confidence=_decimal_setting(
                values,
                "auto_incident_confidence",
                "0.70",
                minimum=Decimal("0"),
                maximum=Decimal("1"),
            ),
            entity_match_threshold=_decimal_setting(
                values,
                "entity_match_threshold",
                "0.65",
                minimum=Decimal("0"),
                maximum=Decimal("1"),
            ),
            entity_review_threshold=_decimal_setting(
                values,
                "entity_review_threshold",
                "0.85",
                minimum=Decimal("0"),
                maximum=Decimal("1"),
            ),
            incident_dedup_hours=dedup_raw,
            capacity_utilization_threshold=_decimal_setting(
                values,
                "capacity_utilization_threshold",
                "0.90",
                minimum=Decimal("0"),
                maximum=Decimal("2"),
            ),
            inventory_on_hand_threshold=_decimal_setting(
                values,
                "inventory_on_hand_threshold",
                "250",
                minimum=Decimal("0"),
                maximum=Decimal("1000000000"),
            ),
        )
        if config.entity_review_threshold < config.entity_match_threshold:
            raise ValueError("entity_review_threshold cannot be lower than entity_match_threshold.")
        if config.auto_incident_confidence < config.minimum_signal_confidence:
            raise ValueError(
                "auto_incident_confidence cannot be lower than minimum_signal_confidence."
            )
        return config


@dataclass(frozen=True, slots=True)
class EntityReference:
    entity_type: str
    value: str
    field: str


@dataclass(frozen=True, slots=True)
class EntityCandidate:
    entity_type: str
    entity_id: UUID
    aliases: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class EntityMatch:
    entity_type: str
    entity_id: UUID
    confidence: Decimal
    method: str
    requires_review: bool
    reference: EntityReference


@dataclass(frozen=True, slots=True)
class NormalizedSignal:
    external_id: str
    occurred_at: datetime
    category: SignalCategory
    severity: Severity
    confidence: Decimal
    title: str
    description: str | None
    location: dict[str, object]
    entity_references: tuple[EntityReference, ...]
    raw_reference: str
    raw_payload: dict[str, object]
    normalized_payload: dict[str, object]
    detection_metadata: dict[str, object] = field(default_factory=dict)

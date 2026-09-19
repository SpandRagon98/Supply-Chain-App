"""Incident deduplication identities and guarded lifecycle transitions."""

import hashlib
import json

from app.core.errors import ApplicationError
from app.domain.enums import IncidentStatus, Severity, SignalCategory
from app.intelligence.contracts import EntityMatch, NormalizedSignal

SEVERITY_RANK = {
    Severity.INFORMATIONAL: 0,
    Severity.LOW: 1,
    Severity.MEDIUM: 2,
    Severity.HIGH: 3,
    Severity.CRITICAL: 4,
}

ALLOWED_INCIDENT_TRANSITIONS: dict[IncidentStatus, frozenset[IncidentStatus]] = {
    IncidentStatus.DETECTED: frozenset(
        {IncidentStatus.UNDER_REVIEW, IncidentStatus.ACTIVE, IncidentStatus.CLOSED}
    ),
    IncidentStatus.UNDER_REVIEW: frozenset({IncidentStatus.ACTIVE, IncidentStatus.CLOSED}),
    IncidentStatus.ACTIVE: frozenset({IncidentStatus.MITIGATION_PROPOSED, IncidentStatus.RESOLVED}),
    IncidentStatus.MITIGATION_PROPOSED: frozenset(
        {IncidentStatus.APPROVAL_PENDING, IncidentStatus.ACTIVE}
    ),
    IncidentStatus.APPROVAL_PENDING: frozenset(
        {IncidentStatus.MITIGATING, IncidentStatus.MITIGATION_PROPOSED}
    ),
    IncidentStatus.MITIGATING: frozenset({IncidentStatus.MONITORING, IncidentStatus.ACTIVE}),
    IncidentStatus.MONITORING: frozenset({IncidentStatus.RESOLVED, IncidentStatus.MITIGATING}),
    IncidentStatus.RESOLVED: frozenset({IncidentStatus.CLOSED}),
    IncidentStatus.CLOSED: frozenset(),
}


def assert_incident_transition(current: IncidentStatus, target: IncidentStatus) -> None:
    if target not in ALLOWED_INCIDENT_TRANSITIONS[current]:
        raise ApplicationError(
            code="invalid_incident_transition",
            message=f"Incident cannot transition from {current.value} to {target.value}.",
            status_code=409,
        )


def deduplication_key(
    signal: NormalizedSignal,
    matches: tuple[EntityMatch, ...],
) -> str:
    location = signal.location
    location_identity = (
        location.get("country_code")
        or location.get("location")
        or location.get("cities")
        or "GLOBAL"
    )
    entity_types: set[str]
    if signal.category in {
        SignalCategory.SUPPLIER_SHUTDOWN,
        SignalCategory.SUPPLIER_DELAY,
        SignalCategory.CAPACITY_PROBLEM,
    }:
        entity_types = (
            {"supplier"}
            if any(match.entity_type == "supplier" for match in matches)
            else {"supplier_site"}
        )
    elif signal.category is SignalCategory.INVENTORY_ANOMALY:
        entity_types = {"material", "facility"}
    elif signal.category in {
        SignalCategory.PORT_CLOSURE,
        SignalCategory.TRANSPORT_DISRUPTION,
        SignalCategory.WEATHER_DISRUPTION,
    }:
        entity_types = set()
    else:
        entity_types = {match.entity_type for match in matches}
    entity_ids = sorted(
        str(match.entity_id) for match in matches if match.entity_type in entity_types
    )
    identity = {
        "category": signal.category.value,
        "location": location_identity,
        "entities": entity_ids,
    }
    digest = hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()
    return f"{signal.category.value}:{digest[:32]}"

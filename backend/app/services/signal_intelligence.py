"""Canonical signal ingestion, entity resolution, deduplication, and lifecycle."""

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from app.connectors.contracts import ConnectorContext, ConnectorRecord
from app.core.errors import ApplicationError
from app.domain.enums import IncidentStatus
from app.domain.models import (
    DisruptionIncident,
    ExternalSignal,
    IncidentEntity,
    IncidentSignal,
)
from app.domain.tenant import TenantContext
from app.intelligence.contracts import (
    EntityMatch,
    NormalizedSignal,
    SignalIntelligenceConfig,
)
from app.intelligence.detection import SignalDetector
from app.intelligence.incidents import (
    SEVERITY_RANK,
    assert_incident_transition,
    deduplication_key,
)
from app.intelligence.resolution import EntityResolver
from app.repositories.signals import SignalRepository


class SignalIntelligenceService:
    def __init__(
        self,
        repository: SignalRepository,
        tenant: TenantContext,
        detector: SignalDetector | None = None,
        resolver: EntityResolver | None = None,
    ) -> None:
        if repository.tenant != tenant:
            raise ValueError("Repository and service tenant contexts must match.")
        self.repository = repository
        self.tenant = tenant
        self.detector = detector or SignalDetector()
        self.resolver = resolver or EntityResolver()

    async def ingest_records(
        self,
        source_key: str,
        connector_context: ConnectorContext,
        records: Sequence[ConnectorRecord],
    ) -> int:
        source = await self.repository.get_source_by_key(source_key)
        if source is None or not source.is_active:
            raise ApplicationError(
                code="signal_source_unavailable",
                message="The configured signal source is unavailable.",
                status_code=409,
            )
        config = SignalIntelligenceConfig.from_mapping(source.configuration)
        candidates = await self.repository.entity_candidates()
        written = 0
        for record in records:
            if await self.repository.get_signal(source.id, record.external_id) is not None:
                continue
            normalized = self.detector.detect(record, config)
            if normalized is None:
                continue
            signal = await self.repository.add(
                ExternalSignal(
                    organization_id=self.tenant.organization_id,
                    source_id=source.id,
                    external_id=normalized.external_id,
                    occurred_at=normalized.occurred_at,
                    received_at=datetime.now(UTC),
                    category=normalized.category,
                    severity=normalized.severity,
                    confidence=normalized.confidence,
                    title=normalized.title,
                    description=normalized.description,
                    location=normalized.location,
                    extracted_entities=[
                        {
                            "entity_type": reference.entity_type,
                            "value": reference.value,
                            "field": reference.field,
                        }
                        for reference in normalized.entity_references
                    ],
                    raw_reference=normalized.raw_reference,
                    raw_payload=normalized.raw_payload,
                    normalized_payload=normalized.normalized_payload,
                    source_lineage={
                        "connector_id": str(connector_context.connector_id),
                        "connector_run_id": str(connector_context.connector_run_id),
                        "record": record.lineage(),
                        "detection": normalized.detection_metadata,
                    },
                )
            )
            matches = self.resolver.resolve(normalized.entity_references, candidates, config)
            await self._group_incident(signal, normalized, matches, config)
            written += 1
        return written

    async def transition_incident(
        self, incident_id: UUID, target: IncidentStatus
    ) -> DisruptionIncident:
        incident = await self.repository.get_incident(incident_id)
        if incident is None:
            raise ApplicationError(
                code="incident_not_found",
                message="The requested incident was not found.",
                status_code=404,
            )
        assert_incident_transition(incident.status, target)
        incident.status = target
        if target is IncidentStatus.RESOLVED:
            incident.resolved_at = datetime.now(UTC)
        await self.repository.flush()
        return incident

    async def _group_incident(
        self,
        signal: ExternalSignal,
        normalized: NormalizedSignal,
        matches: tuple[EntityMatch, ...],
        config: SignalIntelligenceConfig,
    ) -> DisruptionIncident:
        key = deduplication_key(normalized, matches)
        earliest = normalized.occurred_at - timedelta(hours=config.incident_dedup_hours)
        incident = await self.repository.find_open_incident(key, earliest)
        if incident is None:
            needs_review = (
                normalized.confidence < config.auto_incident_confidence
                or any(match.requires_review for match in matches)
                or (bool(normalized.entity_references) and not matches)
            )
            incident = await self.repository.add(
                DisruptionIncident(
                    organization_id=self.tenant.organization_id,
                    incident_number=(
                        f"INC-{normalized.occurred_at.year}-{str(signal.id)[:8].upper()}"
                    ),
                    title=normalized.title,
                    description=normalized.description,
                    incident_type=normalized.category,
                    severity=normalized.severity,
                    confidence=normalized.confidence,
                    status=(
                        IncidentStatus.UNDER_REVIEW if needs_review else IncidentStatus.DETECTED
                    ),
                    started_at=normalized.occurred_at,
                    affected_location=normalized.location,
                    deduplication_key=key,
                )
            )
        else:
            if SEVERITY_RANK[normalized.severity] > SEVERITY_RANK[incident.severity]:
                incident.severity = normalized.severity
            incident.confidence = max(incident.confidence, normalized.confidence)
            await self.repository.flush()

        if await self.repository.get_incident_signal(incident.id, signal.id) is None:
            await self.repository.add(
                IncidentSignal(
                    organization_id=self.tenant.organization_id,
                    incident_id=incident.id,
                    signal_id=signal.id,
                )
            )
        for match in matches:
            existing = await self.repository.get_incident_entity(
                incident.id, match.entity_type, match.entity_id
            )
            if existing is None:
                await self.repository.add(
                    IncidentEntity(
                        organization_id=self.tenant.organization_id,
                        incident_id=incident.id,
                        entity_type=match.entity_type,
                        entity_id=match.entity_id,
                        match_confidence=match.confidence,
                        match_method=match.method,
                        requires_review=match.requires_review,
                    )
                )
            elif Decimal(existing.match_confidence) < match.confidence:
                existing.match_confidence = match.confidence
                existing.match_method = match.method
                existing.requires_review = match.requires_review
                await self.repository.flush()
        return incident


class SignalIngestionSink:
    """Connector sink that writes supported records into signal intelligence."""

    def __init__(self, service: SignalIntelligenceService) -> None:
        self.service = service

    async def write(
        self,
        context: ConnectorContext,
        records: Sequence[ConnectorRecord],
    ) -> int:
        source_key = context.configuration.get("signal_source_key")
        if not isinstance(source_key, str) or not source_key:
            raise ValueError("Connector configuration requires signal_source_key.")
        return await self.service.ingest_records(source_key, context, records)

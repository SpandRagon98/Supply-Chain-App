"""Normalization, detection, resolution, deduplication, and lifecycle tests."""

import os
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.connectors.contracts import ConnectorContext, ConnectorRecord
from app.connectors.mocks import MockNewsAdapter, MockWeatherAdapter, build_mock_connector_registry
from app.core.errors import ApplicationError, TenantIsolationError
from app.domain.base import TenantEntity
from app.domain.enums import IncidentStatus, Severity, SignalCategory
from app.domain.models import (
    Connector,
    DisruptionIncident,
    ExternalSignal,
    IncidentEntity,
    IncidentSignal,
    Organization,
    SignalSource,
)
from app.domain.tenant import TenantContext
from app.intelligence.contracts import (
    EntityCandidate,
    EntityReference,
    SignalIntelligenceConfig,
)
from app.intelligence.detection import SignalDetector
from app.intelligence.incidents import assert_incident_transition
from app.intelligence.normalization import normalize_country, normalize_payload, normalize_unit
from app.intelligence.resolution import EntityResolver
from app.repositories.connectors import ConnectorRepository
from app.repositories.signals import SignalRepository
from app.services.connectors import ConnectorService
from app.services.signal_intelligence import SignalIngestionSink, SignalIntelligenceService

DEFAULT_SOURCE_CONFIG: dict[str, object] = {
    "minimum_signal_confidence": 0.2,
    "auto_incident_confidence": 0.7,
    "entity_match_threshold": 0.65,
    "entity_review_threshold": 0.85,
    "incident_dedup_hours": 72,
    "capacity_utilization_threshold": 0.9,
    "inventory_on_hand_threshold": 250,
}


def connector_context(source_key: str) -> ConnectorContext:
    return ConnectorContext(
        organization_id=uuid4(),
        connector_id=uuid4(),
        connector_run_id=uuid4(),
        configuration={"signal_source_key": source_key},
        checkpoint={},
    )


def test_normalization_preserves_canonical_country_units_and_identifiers() -> None:
    assert normalize_country("Taiwan") == "TW"
    assert normalize_unit(" pieces ") == "EA"
    assert normalize_payload(
        {
            "supplier_code": " formosa ",
            "country": "Taiwan",
            "unit": "each",
        }
    ) == {"supplier_code": "FORMOSA", "country_code": "TW", "unit": "EA"}


def test_signal_configuration_rejects_unsafe_thresholds() -> None:
    with pytest.raises(ValueError, match="cannot be lower"):
        SignalIntelligenceConfig.from_mapping(
            {"entity_match_threshold": 0.9, "entity_review_threshold": 0.8}
        )
    with pytest.raises(ValueError, match="incident_dedup_hours"):
        SignalIntelligenceConfig.from_mapping({"incident_dedup_hours": 0})


async def test_detector_classifies_weather_and_filters_non_signals() -> None:
    context = connector_context("global-weather")
    weather_batch = await MockWeatherAdapter().fetch(context)
    config = SignalIntelligenceConfig()
    detector = SignalDetector()

    signal = detector.detect(weather_batch.records[0], config)
    healthy_inventory = ConnectorRecord(
        external_id="healthy",
        record_type="inventory_snapshot",
        observed_at=datetime(2026, 9, 19, tzinfo=UTC),
        source_uri="mock://erp/healthy",
        payload={"material_sku": "CPU-X9", "on_hand": 900},
    )

    assert signal is not None
    assert signal.category is SignalCategory.WEATHER_DISRUPTION
    assert signal.severity is Severity.HIGH
    assert signal.location["country_code"] == "TW"
    assert {reference.value for reference in signal.entity_references} == {
        "Tainan",
        "Hsinchu",
    }
    assert detector.detect(healthy_inventory, config) is None


def test_entity_resolution_marks_fuzzy_matches_for_review() -> None:
    supplier_id = uuid4()
    exact_site_ids = (uuid4(), uuid4())
    candidates = (
        EntityCandidate(
            "supplier",
            supplier_id,
            (("code", "KYOTO-BATT"), ("name", "Kyoto Battery Systems")),
        ),
        EntityCandidate("supplier_site", exact_site_ids[0], (("city", "Shenzhen"),)),
        EntityCandidate("supplier_site", exact_site_ids[1], (("city", "Shenzhen"),)),
    )
    config = SignalIntelligenceConfig.from_mapping(
        {"entity_match_threshold": 0.6, "entity_review_threshold": 0.95}
    )
    matches = EntityResolver().resolve(
        (
            EntityReference("supplier", "Kyoto Batery Systems", "name"),
            EntityReference("supplier_site", "Shenzhen", "city"),
        ),
        candidates,
        config,
    )

    supplier_match = next(match for match in matches if match.entity_type == "supplier")
    site_matches = [match for match in matches if match.entity_type == "supplier_site"]
    assert supplier_match.entity_id == supplier_id
    assert supplier_match.method == "FUZZY_NAME"
    assert supplier_match.requires_review is True
    assert {match.entity_id for match in site_matches} == set(exact_site_ids)


def test_incident_lifecycle_rejects_skips_and_closed_reactivation() -> None:
    assert_incident_transition(IncidentStatus.DETECTED, IncidentStatus.ACTIVE)
    assert_incident_transition(IncidentStatus.RESOLVED, IncidentStatus.CLOSED)
    with pytest.raises(ApplicationError, match="cannot transition"):
        assert_incident_transition(IncidentStatus.DETECTED, IncidentStatus.APPROVAL_PENDING)
    with pytest.raises(ApplicationError, match="cannot transition"):
        assert_incident_transition(IncidentStatus.CLOSED, IncidentStatus.ACTIVE)


class MemorySignalRepository(SignalRepository):
    def __init__(
        self,
        tenant: TenantContext,
        sources: Sequence[SignalSource],
        candidates: tuple[EntityCandidate, ...],
    ) -> None:
        self.tenant = tenant
        self.sources = list(sources)
        self.candidates = candidates
        self.signals: list[ExternalSignal] = []
        self.incidents: list[DisruptionIncident] = []
        self.incident_signals: list[IncidentSignal] = []
        self.incident_entities: list[IncidentEntity] = []

    async def add[EntityT: TenantEntity](self, entity: EntityT) -> EntityT:
        if entity.organization_id != self.tenant.organization_id:
            raise TenantIsolationError
        entity.id = uuid4()
        if isinstance(entity, ExternalSignal):
            self.signals.append(entity)
        elif isinstance(entity, DisruptionIncident):
            self.incidents.append(entity)
        elif isinstance(entity, IncidentSignal):
            self.incident_signals.append(entity)
        elif isinstance(entity, IncidentEntity):
            self.incident_entities.append(entity)
        return entity

    async def flush(self) -> None:
        return None

    async def get_source_by_key(self, key: str) -> SignalSource | None:
        return next((source for source in self.sources if source.key == key), None)

    async def get_signal(self, source_id: UUID, external_id: str) -> ExternalSignal | None:
        return next(
            (
                signal
                for signal in self.signals
                if signal.source_id == source_id and signal.external_id == external_id
            ),
            None,
        )

    async def get_incident(self, incident_id: UUID) -> DisruptionIncident | None:
        return next((incident for incident in self.incidents if incident.id == incident_id), None)

    async def find_open_incident(
        self, deduplication_key: str, earliest_started_at: datetime
    ) -> DisruptionIncident | None:
        return next(
            (
                incident
                for incident in reversed(self.incidents)
                if incident.deduplication_key == deduplication_key
                and incident.started_at >= earliest_started_at
                and incident.status not in {IncidentStatus.RESOLVED, IncidentStatus.CLOSED}
            ),
            None,
        )

    async def get_incident_signal(
        self, incident_id: UUID, signal_id: UUID
    ) -> IncidentSignal | None:
        return next(
            (
                link
                for link in self.incident_signals
                if link.incident_id == incident_id and link.signal_id == signal_id
            ),
            None,
        )

    async def get_incident_entity(
        self, incident_id: UUID, entity_type: str, entity_id: UUID
    ) -> IncidentEntity | None:
        return next(
            (
                entity
                for entity in self.incident_entities
                if entity.incident_id == incident_id
                and entity.entity_type == entity_type
                and entity.entity_id == entity_id
            ),
            None,
        )

    async def entity_candidates(self) -> tuple[EntityCandidate, ...]:
        return self.candidates


def source(organization_id: UUID, key: str) -> SignalSource:
    return SignalSource(
        id=uuid4(),
        organization_id=organization_id,
        key=key,
        name=key,
        source_type="MOCK",
        is_active=True,
        configuration=dict(DEFAULT_SOURCE_CONFIG),
    )


async def test_signal_sink_deduplicates_weather_and_is_idempotent() -> None:
    tenant = TenantContext(organization_id=uuid4(), user_id=None)
    sites = (
        EntityCandidate("supplier_site", uuid4(), (("city", "Tainan"),)),
        EntityCandidate("supplier_site", uuid4(), (("city", "Hsinchu"),)),
    )
    repository = MemorySignalRepository(
        tenant, (source(tenant.organization_id, "global-weather"),), sites
    )
    service = SignalIntelligenceService(repository, tenant)
    sink = SignalIngestionSink(service)
    context = connector_context("global-weather")
    batch = await MockWeatherAdapter().fetch(context)

    first_written = await sink.write(context, batch.records)
    second_written = await sink.write(context, batch.records)

    assert first_written == 2
    assert second_written == 0
    assert len(repository.signals) == 2
    assert len(repository.incidents) == 1
    assert len(repository.incident_signals) == 2
    assert len(repository.incident_entities) == 2
    assert repository.incidents[0].status is IncidentStatus.DETECTED


async def test_low_confidence_news_incident_requires_review() -> None:
    tenant = TenantContext(organization_id=uuid4(), user_id=None)
    supplier_id = uuid4()
    repository = MemorySignalRepository(
        tenant,
        (source(tenant.organization_id, "trusted-news"),),
        (
            EntityCandidate(
                "supplier",
                supplier_id,
                (("code", "KYOTO-BATT"), ("name", "Kyoto Battery Systems")),
            ),
        ),
    )
    service = SignalIntelligenceService(repository, tenant)
    context = connector_context("trusted-news")
    batch = await MockNewsAdapter().fetch(context)

    assert await SignalIngestionSink(service).write(context, batch.records) == 2
    rumor_incident = next(
        incident
        for incident in repository.incidents
        if incident.incident_type is SignalCategory.SUPPLIER_SHUTDOWN
    )
    assert rumor_incident.status is IncidentStatus.UNDER_REVIEW
    assert rumor_incident.confidence == Decimal("0.31")
    assert repository.incident_entities[0].entity_id == supplier_id

    active = await service.transition_incident(rumor_incident.id, IncidentStatus.ACTIVE)
    assert active.status is IncidentStatus.ACTIVE


async def test_signal_service_rejects_missing_sources_and_invalid_sink_config() -> None:
    tenant = TenantContext(organization_id=uuid4(), user_id=None)
    repository = MemorySignalRepository(tenant, (), ())
    service = SignalIntelligenceService(repository, tenant)
    record = ConnectorRecord(
        external_id="manual-1",
        record_type="manual_disruption",
        observed_at=datetime(2026, 9, 19, tzinfo=UTC),
        payload={"category": "MANUAL_DISRUPTION"},
        source_uri="manual://manual-1",
    )

    with pytest.raises(ApplicationError, match="source is unavailable"):
        await service.ingest_records("missing", connector_context("missing"), (record,))
    with pytest.raises(ValueError, match="signal_source_key"):
        await SignalIngestionSink(service).write(
            ConnectorContext(
                organization_id=tenant.organization_id,
                connector_id=uuid4(),
                connector_run_id=uuid4(),
                configuration={},
                checkpoint={},
            ),
            (record,),
        )
    with pytest.raises(ApplicationError, match="incident was not found"):
        await service.transition_incident(uuid4(), IncidentStatus.ACTIVE)


async def test_all_mock_feeds_group_into_five_incidents_without_database() -> None:
    tenant = TenantContext(organization_id=uuid4(), user_id=None)
    source_keys = (
        "trusted-news",
        "global-weather",
        "nova-erp",
        "ocean-tracking",
        "supplier-feed",
    )
    candidates = (
        EntityCandidate(
            "supplier",
            uuid4(),
            (("code", "KYOTO-BATT"), ("name", "Kyoto Battery Systems")),
        ),
        EntityCandidate("supplier", uuid4(), (("code", "FORMOSA"),)),
        EntityCandidate("supplier_site", uuid4(), (("code", "KYOTO-BATT-01"),)),
        EntityCandidate("supplier_site", uuid4(), (("city", "Tainan"),)),
        EntityCandidate("supplier_site", uuid4(), (("city", "Hsinchu"),)),
        EntityCandidate("material", uuid4(), (("sku", "CPU-X9"),)),
        EntityCandidate("material", uuid4(), (("sku", "CELL-LI6"),)),
        EntityCandidate("facility", uuid4(), (("code", "PUNE-PLANT"),)),
    )
    repository = MemorySignalRepository(
        tenant,
        tuple(source(tenant.organization_id, key) for key in source_keys),
        candidates,
    )
    sink = SignalIngestionSink(SignalIntelligenceService(repository, tenant))
    registry = build_mock_connector_registry()
    references = (
        ("mock.news", "1.0", "trusted-news"),
        ("mock.weather", "1.0", "global-weather"),
        ("mock.erp", "1.0", "nova-erp"),
        ("mock.shipment", "1.0", "ocean-tracking"),
        ("mock.supplier", "1.0", "supplier-feed"),
    )

    written = 0
    for adapter_key, version, source_key in references:
        context = connector_context(source_key)
        batch = await registry.get(adapter_key, version).fetch(context)
        written += await sink.write(context, batch.records)

    assert written == 10
    assert len(repository.signals) == 10
    assert len(repository.incidents) == 5
    port_incident = next(
        incident
        for incident in repository.incidents
        if incident.incident_type is SignalCategory.PORT_CLOSURE
    )
    shutdown_incident = next(
        incident
        for incident in repository.incidents
        if incident.incident_type is SignalCategory.SUPPLIER_SHUTDOWN
    )
    assert sum(link.incident_id == port_incident.id for link in repository.incident_signals) == 4
    assert shutdown_incident.status is IncidentStatus.UNDER_REVIEW
    assert shutdown_incident.confidence == Decimal("1.0")
    assert shutdown_incident.severity is Severity.CRITICAL


@pytest.mark.asyncio
async def test_postgresql_full_mock_ingestion_creates_canonical_incidents() -> None:
    database_url = os.getenv("TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip("TEST_DATABASE_URL is only configured for PostgreSQL CI integration tests")

    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            transaction = await session.begin()
            organization = await session.scalar(
                select(Organization).where(Organization.slug == "nova-electronics")
            )
            assert organization is not None
            initial_signal_count = int(
                await session.scalar(
                    select(func.count())
                    .select_from(ExternalSignal)
                    .where(ExternalSignal.organization_id == organization.id)
                )
                or 0
            )
            initial_incident_count = int(
                await session.scalar(
                    select(func.count())
                    .select_from(DisruptionIncident)
                    .where(DisruptionIncident.organization_id == organization.id)
                )
                or 0
            )
            initial_port_signal_count = int(
                await session.scalar(
                    select(func.count())
                    .select_from(IncidentSignal)
                    .join(
                        DisruptionIncident,
                        DisruptionIncident.id == IncidentSignal.incident_id,
                    )
                    .where(
                        IncidentSignal.organization_id == organization.id,
                        DisruptionIncident.incident_type == SignalCategory.PORT_CLOSURE,
                    )
                )
                or 0
            )
            tenant = TenantContext(organization_id=organization.id, user_id=None)
            signal_repository = SignalRepository(session, tenant)
            sink = SignalIngestionSink(SignalIntelligenceService(signal_repository, tenant))
            connector_repository = ConnectorRepository(session, tenant)
            connector_service = ConnectorService(
                connector_repository, build_mock_connector_registry(), tenant
            )
            connectors = tuple(
                await session.scalars(
                    select(Connector)
                    .where(Connector.organization_id == organization.id)
                    .order_by(Connector.key)
                )
            )
            connector_priority = {
                "trusted-news": 0,
                "global-weather": 1,
                "nova-erp": 2,
                "ocean-tracking": 3,
                "supplier-feed": 4,
            }
            connectors = tuple(sorted(connectors, key=lambda item: connector_priority[item.key]))

            results = [
                await connector_service.run(connector.id, sink=sink) for connector in connectors
            ]
            signal_count = await session.scalar(
                select(func.count())
                .select_from(ExternalSignal)
                .where(ExternalSignal.organization_id == organization.id)
            )
            incident_count = await session.scalar(
                select(func.count())
                .select_from(DisruptionIncident)
                .where(DisruptionIncident.organization_id == organization.id)
            )
            port_signal_count = await session.scalar(
                select(func.count())
                .select_from(IncidentSignal)
                .join(
                    DisruptionIncident,
                    DisruptionIncident.id == IncidentSignal.incident_id,
                )
                .where(
                    IncidentSignal.organization_id == organization.id,
                    DisruptionIncident.incident_type == SignalCategory.PORT_CLOSURE,
                )
            )
            shutdown_incident = await session.scalar(
                select(DisruptionIncident).where(
                    DisruptionIncident.organization_id == organization.id,
                    DisruptionIncident.incident_type == SignalCategory.SUPPLIER_SHUTDOWN,
                )
            )

            assert len(connectors) == 5
            assert sum(result.records_written for result in results) == 10
            assert signal_count == initial_signal_count + 10
            assert incident_count == initial_incident_count + 5
            assert port_signal_count == initial_port_signal_count + 4
            assert shutdown_incident is not None
            assert shutdown_incident.status is IncidentStatus.UNDER_REVIEW
            assert shutdown_incident.severity is Severity.CRITICAL
            assert shutdown_incident.confidence == Decimal("1.00000")
            await transaction.rollback()
    finally:
        await engine.dispose()

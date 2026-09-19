"""Connector contracts, mocks, checkpointing, lineage, and persistence tests."""

import os
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.connectors.contracts import (
    ConnectorBatch,
    ConnectorContext,
    ConnectorRecord,
)
from app.connectors.mocks import MockERPAdapter, build_mock_connector_registry
from app.connectors.registry import ConnectorRegistry
from app.core.errors import (
    ConnectorNotFoundError,
    ConnectorUnavailableError,
    TenantIsolationError,
)
from app.domain.enums import ConnectorStatus, RunStatus
from app.domain.models import Connector, ConnectorRun, Organization
from app.domain.tenant import TenantContext
from app.repositories.connectors import ConnectorRepository
from app.services.connectors import ConnectorService


def make_context(*, checkpoint: dict[str, object] | None = None) -> ConnectorContext:
    return ConnectorContext(
        organization_id=uuid4(),
        connector_id=uuid4(),
        connector_run_id=uuid4(),
        configuration={"mode": "mock"},
        checkpoint=checkpoint or {},
    )


def make_connector(
    organization_id: UUID,
    *,
    adapter: str = "mock.erp@1.0",
    status: ConnectorStatus = ConnectorStatus.MOCK_MODE,
) -> Connector:
    return Connector(
        id=uuid4(),
        organization_id=organization_id,
        key=f"connector-{uuid4()}",
        name="Test Connector",
        connector_type="TEST",
        adapter=adapter,
        status=status,
        configuration={"mode": "mock"},
    )


def test_connector_record_hash_and_lineage_are_deterministic() -> None:
    first = ConnectorRecord(
        external_id="record-1",
        record_type="inventory_snapshot",
        observed_at=datetime(2026, 9, 19, tzinfo=UTC),
        payload={"sku": "CPU-X9", "quantity": 190},
        source_uri="mock://erp/record-1",
    )
    second = ConnectorRecord(
        external_id="record-1",
        record_type="inventory_snapshot",
        observed_at=datetime(2026, 9, 19, tzinfo=UTC),
        payload={"quantity": 190, "sku": "CPU-X9"},
        source_uri="mock://erp/record-1",
    )

    assert first.payload_hash == second.payload_hash
    assert first.lineage()["payload_sha256"] == first.payload_hash
    assert "payload" not in first.lineage()


def test_connector_contract_rejects_ambiguous_records_and_batches() -> None:
    with pytest.raises(ValueError, match="timestamps"):
        ConnectorRecord(
            external_id="record-1",
            record_type="test",
            observed_at=datetime(2026, 9, 19),
            payload={},
            source_uri="mock://test/record-1",
        )

    record = ConnectorRecord(
        external_id="duplicate",
        record_type="test",
        observed_at=datetime(2026, 9, 19, tzinfo=UTC),
        payload={},
        source_uri="mock://test/duplicate",
    )
    with pytest.raises(ValueError, match="duplicate external IDs"):
        ConnectorBatch(records=(record, record))


async def test_mock_adapters_cover_required_offline_sources() -> None:
    registry = build_mock_connector_registry()
    expected = {
        ("mock.erp", "1.0"),
        ("mock.news", "1.0"),
        ("mock.shipment", "1.0"),
        ("mock.supplier", "1.0"),
        ("mock.weather", "1.0"),
    }

    assert set(registry.references) == expected
    batches = {
        key: await registry.get(key, version).fetch(make_context())
        for key, version in registry.references
    }
    assert sum(len(batch.records) for batch in batches.values()) == 12
    assert batches["mock.weather"].records[0].payload["event"] == "TYPHOON"
    assert batches["mock.news"].records[1].payload["confidence"] == 0.31
    assert batches["mock.supplier"].records[0].payload["event"] == "PLANT_SHUTDOWN"
    assert batches["mock.shipment"].records[0].payload["reason"] == "PORT_CLOSURE"


def test_connector_registry_rejects_duplicate_and_missing_adapters() -> None:
    registry = ConnectorRegistry()
    adapter = MockERPAdapter()
    registry.register(adapter)

    with pytest.raises(ValueError, match="already registered"):
        registry.register(adapter)
    with pytest.raises(ConnectorNotFoundError):
        registry.get("missing", "1.0")


class MemoryConnectorRepository(ConnectorRepository):
    def __init__(self, tenant: TenantContext, connector: Connector | None) -> None:
        self.tenant = tenant
        self.connector = connector
        self.runs: list[ConnectorRun] = []

    async def get(self, connector_id: UUID) -> Connector | None:
        if self.connector is not None and self.connector.id == connector_id:
            return self.connector
        return None

    async def add(self, connector: Connector) -> Connector:
        if connector.organization_id != self.tenant.organization_id:
            raise TenantIsolationError
        self.connector = connector
        return connector

    async def add_run(self, run: ConnectorRun) -> ConnectorRun:
        if run.organization_id != self.tenant.organization_id:
            raise TenantIsolationError
        run.id = uuid4()
        self.runs.append(run)
        return run

    async def latest_successful_run(self, connector_id: UUID) -> ConnectorRun | None:
        return next(
            (
                run
                for run in reversed(self.runs)
                if run.connector_id == connector_id and run.status is RunStatus.SUCCEEDED
            ),
            None,
        )

    async def flush(self) -> None:
        return None


@dataclass
class CapturingSink:
    records: list[ConnectorRecord] = field(default_factory=list)

    async def write(
        self,
        context: ConnectorContext,
        records: Sequence[ConnectorRecord],
    ) -> int:
        assert context.organization_id
        self.records.extend(records)
        return len(records)


async def test_connector_service_persists_lineage_and_advances_checkpoint() -> None:
    tenant = TenantContext(organization_id=uuid4(), user_id=uuid4())
    connector = make_connector(tenant.organization_id)
    repository = MemoryConnectorRepository(tenant, connector)
    sink = CapturingSink()
    service = ConnectorService(repository, build_mock_connector_registry(), tenant)

    first = await service.run(connector.id, sink=sink)
    second = await service.run(connector.id, sink=sink)

    assert first.status is RunStatus.SUCCEEDED
    assert first.records_written == 3
    assert first.checkpoint["cursor"] == 3
    assert second.checkpoint["cursor"] == 6
    assert len(sink.records) == 6
    assert connector.status is ConnectorStatus.MOCK_MODE
    assert connector.last_sync_at is not None
    assert repository.runs[0].lineage["adapter"] == "mock.erp"
    lineage_records = repository.runs[0].lineage["records"]
    assert isinstance(lineage_records, list)
    assert len(lineage_records) == 3
    assert all("payload_sha256" in item for item in lineage_records)


class FailingAdapter:
    key = "test.failure"
    version = "1.0"

    async def fetch(self, context: ConnectorContext) -> ConnectorBatch:
        del context
        raise TimeoutError("upstream did not respond")


async def test_connector_failure_is_a_durable_non_secret_result() -> None:
    tenant = TenantContext(organization_id=uuid4(), user_id=None)
    connector = make_connector(tenant.organization_id, adapter="test.failure@1.0")
    repository = MemoryConnectorRepository(tenant, connector)
    registry = ConnectorRegistry()
    registry.register(FailingAdapter())

    result = await ConnectorService(repository, registry, tenant).run(connector.id)

    assert result.status is RunStatus.FAILED
    assert result.error_code == "TimeoutError"
    assert result.error_message == "upstream did not respond"
    assert result.records == ()
    assert connector.status is ConnectorStatus.ERROR
    assert repository.runs[0].status is RunStatus.FAILED


async def test_connector_service_rejects_unavailable_configuration() -> None:
    tenant = TenantContext(organization_id=uuid4(), user_id=None)
    missing_repository = MemoryConnectorRepository(tenant, None)
    service = ConnectorService(missing_repository, ConnectorRegistry(), tenant)

    with pytest.raises(ConnectorNotFoundError):
        await service.run(uuid4())

    disconnected = make_connector(tenant.organization_id, status=ConnectorStatus.DISCONNECTED)
    service = ConnectorService(
        MemoryConnectorRepository(tenant, disconnected), ConnectorRegistry(), tenant
    )
    with pytest.raises(ConnectorUnavailableError, match="Disconnected"):
        await service.run(disconnected.id)

    malformed = make_connector(tenant.organization_id, adapter="not-versioned")
    service = ConnectorService(
        MemoryConnectorRepository(tenant, malformed), ConnectorRegistry(), tenant
    )
    with pytest.raises(ConnectorUnavailableError, match="<key>@<version>"):
        await service.run(malformed.id)


@pytest.mark.asyncio
async def test_postgresql_connector_run_persists_lineage() -> None:
    database_url = os.getenv("TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip("TEST_DATABASE_URL is only configured for PostgreSQL CI integration tests")

    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    organization_id = uuid4()
    try:
        async with session_factory() as session:
            transaction = await session.begin()
            organization = Organization(
                id=organization_id,
                name="Connector Test Tenant",
                slug=f"connector-test-{organization_id}",
            )
            connector = make_connector(organization_id)
            session.add_all((organization, connector))
            await session.flush()

            tenant = TenantContext(organization_id=organization_id, user_id=None)
            repository = ConnectorRepository(session, tenant)
            result = await ConnectorService(
                repository, build_mock_connector_registry(), tenant
            ).run(connector.id, sink=CapturingSink())
            persisted_count = await session.scalar(
                select(func.count())
                .select_from(ConnectorRun)
                .where(ConnectorRun.organization_id == organization_id)
            )
            persisted_run = await session.scalar(
                select(ConnectorRun).where(ConnectorRun.id == result.connector_run_id)
            )

            assert result.status is RunStatus.SUCCEEDED
            assert persisted_count == 1
            assert persisted_run is not None
            assert persisted_run.records_read == 3
            assert persisted_run.records_written == 3
            persisted_lineage = persisted_run.lineage["records"]
            assert isinstance(persisted_lineage, list)
            assert len(persisted_lineage) == 3
            await transaction.rollback()
    finally:
        await engine.dispose()

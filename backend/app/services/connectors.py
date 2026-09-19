"""Checkpointed connector execution with durable telemetry and lineage."""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from app.connectors.contracts import (
    ConnectorContext,
    ConnectorRecord,
    ConnectorSink,
    DiscardingConnectorSink,
)
from app.connectors.registry import ConnectorRegistry
from app.core.errors import ConnectorNotFoundError, ConnectorUnavailableError
from app.domain.enums import ConnectorStatus, RunStatus
from app.domain.models import Connector, ConnectorRun
from app.domain.tenant import TenantContext
from app.repositories.connectors import ConnectorRepository


@dataclass(frozen=True, slots=True)
class ConnectorExecutionResult:
    connector_run_id: UUID
    status: RunStatus
    records: tuple[ConnectorRecord, ...]
    records_written: int
    checkpoint: dict[str, object]
    error_code: str | None = None
    error_message: str | None = None


class ConnectorService:
    def __init__(
        self,
        repository: ConnectorRepository,
        registry: ConnectorRegistry,
        tenant: TenantContext,
    ) -> None:
        if repository.tenant != tenant:
            raise ValueError("Repository and service tenant contexts must match.")
        self.repository = repository
        self.registry = registry
        self.tenant = tenant

    async def run(
        self,
        connector_id: UUID,
        *,
        sink: ConnectorSink | None = None,
    ) -> ConnectorExecutionResult:
        connector = await self.repository.get(connector_id)
        if connector is None:
            raise ConnectorNotFoundError("connector")
        if connector.status is ConnectorStatus.DISCONNECTED:
            raise ConnectorUnavailableError("Disconnected connectors cannot run.")

        adapter_key, adapter_version = self._parse_adapter_reference(connector.adapter)
        prior_run = await self.repository.latest_successful_run(connector.id)
        prior_checkpoint = dict(prior_run.checkpoint) if prior_run is not None else {}
        run = ConnectorRun(
            organization_id=self.tenant.organization_id,
            connector_id=connector.id,
            status=RunStatus.RUNNING,
            started_at=datetime.now(UTC),
            records_read=0,
            records_written=0,
            checkpoint=prior_checkpoint,
            lineage={},
        )
        await self.repository.add_run(run)
        context = ConnectorContext(
            organization_id=self.tenant.organization_id,
            connector_id=connector.id,
            connector_run_id=run.id,
            configuration=dict(connector.configuration),
            checkpoint=prior_checkpoint,
        )

        try:
            adapter = self.registry.get(adapter_key, adapter_version)
            batch = await adapter.fetch(context)
            target_sink = sink or DiscardingConnectorSink()
            records_written = await target_sink.write(context, batch.records)
            if records_written < 0 or records_written > len(batch.records):
                raise ValueError("Connector sink returned an invalid records-written count.")

            completed_at = datetime.now(UTC)
            run.status = RunStatus.SUCCEEDED
            run.completed_at = completed_at
            run.records_read = len(batch.records)
            run.records_written = records_written
            run.checkpoint = dict(batch.next_checkpoint)
            run.lineage = {
                "adapter": adapter_key,
                "adapter_version": adapter_version,
                "previous_checkpoint": prior_checkpoint,
                "batch_metadata": dict(batch.metadata),
                "records": [record.lineage() for record in batch.records],
            }
            run.error_code = None
            run.error_message = None
            connector.last_sync_at = completed_at
            connector.last_error = None
            connector.status = self._healthy_status(connector)
            await self.repository.flush()
            return ConnectorExecutionResult(
                connector_run_id=run.id,
                status=run.status,
                records=batch.records,
                records_written=records_written,
                checkpoint=dict(run.checkpoint),
            )
        except Exception as error:  # noqa: BLE001 - connector failures become durable results
            completed_at = datetime.now(UTC)
            run.status = RunStatus.FAILED
            run.completed_at = completed_at
            run.error_code = type(error).__name__
            run.error_message = str(error)[:2000]
            run.lineage = {
                "adapter": adapter_key,
                "adapter_version": adapter_version,
                "previous_checkpoint": prior_checkpoint,
                "failure_at": completed_at.isoformat(),
            }
            connector.status = ConnectorStatus.ERROR
            connector.last_error = run.error_message
            await self.repository.flush()
            return ConnectorExecutionResult(
                connector_run_id=run.id,
                status=run.status,
                records=(),
                records_written=0,
                checkpoint=prior_checkpoint,
                error_code=run.error_code,
                error_message=run.error_message,
            )

    @staticmethod
    def _parse_adapter_reference(reference: str) -> tuple[str, str]:
        key, separator, version = reference.rpartition("@")
        if not separator or not key or not version:
            raise ConnectorUnavailableError(
                "Connector adapter references must use the form '<key>@<version>'."
            )
        return key, version

    @staticmethod
    def _healthy_status(connector: Connector) -> ConnectorStatus:
        return (
            ConnectorStatus.MOCK_MODE
            if connector.configuration.get("mode") == "mock"
            else ConnectorStatus.CONNECTED
        )

"""Connector contracts and source-lineage primitives."""

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ConnectorRecord:
    """One immutable raw record retrieved from an external system."""

    external_id: str
    record_type: str
    observed_at: datetime
    payload: dict[str, object]
    source_uri: str
    metadata: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.external_id.strip() or not self.record_type.strip():
            raise ValueError("Connector records require external_id and record_type.")
        if self.observed_at.tzinfo is None:
            raise ValueError("Connector record timestamps must include a timezone.")

    @property
    def payload_hash(self) -> str:
        canonical = json.dumps(
            self.payload,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode()
        return hashlib.sha256(canonical).hexdigest()

    def lineage(self) -> dict[str, object]:
        return {
            "external_id": self.external_id,
            "record_type": self.record_type,
            "observed_at": self.observed_at.isoformat(),
            "source_uri": self.source_uri,
            "payload_sha256": self.payload_hash,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class ConnectorContext:
    organization_id: UUID
    connector_id: UUID
    connector_run_id: UUID
    configuration: Mapping[str, object]
    checkpoint: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class ConnectorBatch:
    records: tuple[ConnectorRecord, ...]
    next_checkpoint: dict[str, object] = field(default_factory=dict)
    metadata: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        external_ids = [record.external_id for record in self.records]
        if len(external_ids) != len(set(external_ids)):
            raise ValueError("A connector batch cannot contain duplicate external IDs.")


class ConnectorAdapter(Protocol):
    key: str
    version: str

    async def fetch(self, context: ConnectorContext) -> ConnectorBatch:
        """Fetch one checkpointed batch without performing persistence."""

        ...


class ConnectorSink(Protocol):
    async def write(
        self,
        context: ConnectorContext,
        records: Sequence[ConnectorRecord],
    ) -> int:
        """Map raw records into a downstream canonical ingestion boundary."""

        ...


class DiscardingConnectorSink:
    """Explicit no-op sink used when a caller only needs a connector probe."""

    async def write(
        self,
        context: ConnectorContext,
        records: Sequence[ConnectorRecord],
    ) -> int:
        del context, records
        return 0

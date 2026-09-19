"""Stable contracts implemented by every executable workflow stage."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol
from uuid import UUID

from app.domain.enums import RunStatus


@dataclass(frozen=True, slots=True)
class StageExecutionContext:
    """Tenant-safe identifiers and accumulated structured workflow context."""

    organization_id: UUID
    workflow_run_id: UUID
    stage_run_id: UUID
    values: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class StageResult:
    """Structured stage outcome; numeric truth remains owned by stage code."""

    output: dict[str, object] = field(default_factory=dict)
    context_updates: dict[str, object] = field(default_factory=dict)
    status: RunStatus = RunStatus.SUCCEEDED

    def __post_init__(self) -> None:
        if self.status not in {RunStatus.SUCCEEDED, RunStatus.WAITING_FOR_APPROVAL}:
            raise ValueError("A stage result must succeed or wait for approval.")


class StageHandler(Protocol):
    """Common interface for registry-backed workflow stages."""

    key: str
    version: str

    async def execute(
        self,
        context: StageExecutionContext,
        config: Mapping[str, object],
    ) -> StageResult:
        """Execute one deterministic, independently testable workflow stage."""

        ...

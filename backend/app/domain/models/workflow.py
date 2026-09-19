"""Configurable and versioned workflow persistence models."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.base import TenantEntity
from app.domain.enums import FailurePolicy, RunStatus, WorkflowVersionStatus


class WorkflowDefinition(TenantEntity):
    __tablename__ = "workflow_definitions"
    __table_args__ = (UniqueConstraint("organization_id", "key"),)

    key: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class WorkflowVersion(TenantEntity):
    __tablename__ = "workflow_versions"
    __table_args__ = (UniqueConstraint("organization_id", "workflow_definition_id", "version"),)

    workflow_definition_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("workflow_definitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[WorkflowVersionStatus] = mapped_column(
        Enum(WorkflowVersionStatus, native_enum=False, length=20), nullable=False, index=True
    )
    cloned_from_version_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("workflow_versions.id", ondelete="SET NULL")
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    change_summary: Mapped[str | None] = mapped_column(Text)


class StageDefinition(TenantEntity):
    __tablename__ = "stage_definitions"
    __table_args__ = (UniqueConstraint("organization_id", "workflow_version_id", "key"),)

    workflow_version_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("workflow_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    stage_type: Mapped[str] = mapped_column(String(80), nullable=False)
    handler: Mapped[str] = mapped_column(String(255), nullable=False)
    handler_version: Mapped[str] = mapped_column(String(40), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    input_schema: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    output_schema: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    configuration_schema: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)


class StageConfiguration(TenantEntity):
    __tablename__ = "stage_configurations"
    __table_args__ = (UniqueConstraint("organization_id", "stage_definition_id"),)

    stage_definition_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("stage_definitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    configuration: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    retry_policy: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=300, nullable=False)
    failure_policy: Mapped[FailurePolicy] = mapped_column(
        Enum(FailurePolicy, native_enum=False, length=24),
        default=FailurePolicy.FAIL_WORKFLOW,
        nullable=False,
    )
    approval_requirements: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    ai_configuration: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)


class StageDependency(TenantEntity):
    __tablename__ = "stage_dependencies"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "workflow_version_id", "stage_definition_id", "depends_on_stage_id"
        ),
    )

    workflow_version_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("workflow_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stage_definition_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("stage_definitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    depends_on_stage_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("stage_definitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    condition: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)


class WorkflowRun(TenantEntity):
    __tablename__ = "workflow_runs"

    workflow_version_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("workflow_versions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    incident_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("disruption_incidents.id", ondelete="SET NULL"), index=True
    )
    replay_of_run_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("workflow_runs.id", ondelete="SET NULL"), index=True
    )
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus, native_enum=False, length=24), nullable=False, index=True
    )
    is_simulation: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    simulation_parameters: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    context: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)


class StageRun(TenantEntity):
    __tablename__ = "stage_runs"
    __table_args__ = (
        UniqueConstraint("organization_id", "workflow_run_id", "stage_definition_id"),
    )

    workflow_run_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("workflow_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stage_definition_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("stage_definitions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus, native_enum=False, length=24), nullable=False, index=True
    )
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    input_payload: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    output_payload: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    error_code: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)

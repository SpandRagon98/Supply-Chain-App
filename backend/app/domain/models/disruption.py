"""Signals, incidents, deterministic assessments, decisions, and execution models."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.base import TenantEntity
from app.domain.enums import (
    ApprovalStatus,
    ExecutionStatus,
    IncidentStatus,
    RiskBand,
    ScenarioStatus,
    Severity,
    SignalCategory,
    VerificationStatus,
)


class SignalSource(TenantEntity):
    __tablename__ = "signal_sources"
    __table_args__ = (UniqueConstraint("organization_id", "key"),)

    key: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    source_type: Mapped[str] = mapped_column(String(80), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    configuration: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)


class ExternalSignal(TenantEntity):
    __tablename__ = "external_signals"
    __table_args__ = (UniqueConstraint("organization_id", "source_id", "external_id"),)

    source_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("signal_sources.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    category: Mapped[SignalCategory] = mapped_column(
        Enum(SignalCategory, native_enum=False, length=40), nullable=False, index=True
    )
    severity: Mapped[Severity] = mapped_column(
        Enum(Severity, native_enum=False, length=20), nullable=False, index=True
    )
    confidence: Mapped[Decimal] = mapped_column(Numeric(6, 5), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    location: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    extracted_entities: Mapped[list[dict[str, object]]] = mapped_column(JSONB, default=list)
    raw_reference: Mapped[str | None] = mapped_column(String(500))
    raw_payload: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    normalized_payload: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    source_lineage: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)


class DisruptionIncident(TenantEntity):
    __tablename__ = "disruption_incidents"
    __table_args__ = (UniqueConstraint("organization_id", "incident_number"),)

    incident_number: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    incident_type: Mapped[SignalCategory] = mapped_column(
        Enum(SignalCategory, native_enum=False, length=40), nullable=False, index=True
    )
    severity: Mapped[Severity] = mapped_column(
        Enum(Severity, native_enum=False, length=20), nullable=False, index=True
    )
    confidence: Mapped[Decimal] = mapped_column(Numeric(6, 5), nullable=False)
    status: Mapped[IncidentStatus] = mapped_column(
        Enum(IncidentStatus, native_enum=False, length=32), nullable=False, index=True
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expected_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    affected_location: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    deduplication_key: Mapped[str | None] = mapped_column(String(255), index=True)
    workflow_version_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("workflow_versions.id", ondelete="SET NULL"), index=True
    )


class IncidentSignal(TenantEntity):
    __tablename__ = "incident_signals"
    __table_args__ = (UniqueConstraint("organization_id", "incident_id", "signal_id"),)

    incident_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("disruption_incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    signal_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("external_signals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )


class IncidentEntity(TenantEntity):
    __tablename__ = "incident_entities"
    __table_args__ = (
        UniqueConstraint("organization_id", "incident_id", "entity_type", "entity_id"),
    )

    incident_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("disruption_incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    match_confidence: Mapped[Decimal] = mapped_column(Numeric(6, 5), nullable=False)
    match_method: Mapped[str] = mapped_column(String(80), nullable=False)
    requires_review: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reviewed_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ImpactAssessment(TenantEntity):
    __tablename__ = "impact_assessments"

    incident_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("disruption_incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workflow_run_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("workflow_runs.id", ondelete="SET NULL"), index=True
    )
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    calculation_version: Mapped[str] = mapped_column(String(40), nullable=False)
    summary: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)


class ImpactMetric(TenantEntity):
    __tablename__ = "impact_metrics"
    __table_args__ = (UniqueConstraint("organization_id", "assessment_id", "metric_key"),)

    assessment_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("impact_assessments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    metric_key: Mapped[str] = mapped_column(String(100), nullable=False)
    numeric_value: Mapped[Decimal | None] = mapped_column(Numeric(24, 6))
    text_value: Mapped[str | None] = mapped_column(String(500))
    unit: Mapped[str | None] = mapped_column(String(40))
    currency: Mapped[str | None] = mapped_column(String(3))
    lineage: Mapped[list[dict[str, object]]] = mapped_column(JSONB, default=list)


class RiskAssessment(TenantEntity):
    __tablename__ = "risk_assessments"

    incident_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("disruption_incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    impact_assessment_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("impact_assessments.id", ondelete="SET NULL"), index=True
    )
    workflow_run_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("workflow_runs.id", ondelete="SET NULL"), index=True
    )
    score: Mapped[Decimal] = mapped_column(Numeric(6, 3), nullable=False)
    band: Mapped[RiskBand] = mapped_column(
        Enum(RiskBand, native_enum=False, length=16), nullable=False, index=True
    )
    model_version: Mapped[str] = mapped_column(String(40), nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RiskFactor(TenantEntity):
    __tablename__ = "risk_factors"
    __table_args__ = (UniqueConstraint("organization_id", "risk_assessment_id", "factor_key"),)

    risk_assessment_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("risk_assessments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    factor_key: Mapped[str] = mapped_column(String(100), nullable=False)
    raw_value: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    normalized_value: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)
    weight: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)
    contribution: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    lineage: Mapped[list[dict[str, object]]] = mapped_column(JSONB, default=list)


class Scenario(TenantEntity):
    __tablename__ = "scenarios"

    incident_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("disruption_incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workflow_run_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("workflow_runs.id", ondelete="SET NULL"), index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ScenarioStatus] = mapped_column(
        Enum(ScenarioStatus, native_enum=False, length=20), nullable=False, index=True
    )
    incremental_cost: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    delay_days: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    quantity_protected: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    orders_protected: Mapped[int] = mapped_column(Integer, nullable=False)
    revenue_protected: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    expected_service_level: Mapped[Decimal] = mapped_column(Numeric(8, 5), nullable=False)
    feasibility_score: Mapped[Decimal] = mapped_column(Numeric(8, 5), nullable=False)
    objective_score: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    assumptions: Mapped[list[dict[str, object]]] = mapped_column(JSONB, default=list)
    constraints: Mapped[list[dict[str, object]]] = mapped_column(JSONB, default=list)
    calculation_lineage: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)


class ScenarioAction(TenantEntity):
    __tablename__ = "scenario_actions"

    scenario_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("scenarios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    action_type: Mapped[str] = mapped_column(String(80), nullable=False)
    parameters: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    incremental_cost: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=0, nullable=False)
    expected_delay_days: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    feasibility: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)


class Recommendation(TenantEntity):
    __tablename__ = "recommendations"

    incident_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("disruption_incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recommended_scenario_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("scenarios.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    workflow_run_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("workflow_runs.id", ondelete="SET NULL"), index=True
    )
    confidence: Mapped[Decimal] = mapped_column(Numeric(8, 5), nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text)
    alternative_scenario_ids: Mapped[list[str]] = mapped_column(JSONB, default=list)
    assumptions: Mapped[list[dict[str, object]]] = mapped_column(JSONB, default=list)
    risks: Mapped[list[dict[str, object]]] = mapped_column(JSONB, default=list)
    structured_summary: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)


class ApprovalRequest(TenantEntity):
    __tablename__ = "approval_requests"

    recommendation_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("recommendations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[ApprovalStatus] = mapped_column(
        Enum(ApprovalStatus, native_enum=False, length=20), nullable=False, index=True
    )
    requested_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    required_role_key: Mapped[str] = mapped_column(String(40), nullable=False)
    assigned_approver_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    policy_snapshot: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)


class ApprovalDecision(TenantEntity):
    __tablename__ = "approval_decisions"

    approval_request_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("approval_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    decided_by_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    decision: Mapped[ApprovalStatus] = mapped_column(
        Enum(ApprovalStatus, native_enum=False, length=20), nullable=False
    )
    comment: Mapped[str | None] = mapped_column(Text)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ExecutionAction(TenantEntity):
    __tablename__ = "execution_actions"
    __table_args__ = (UniqueConstraint("organization_id", "idempotency_key"),)

    recommendation_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("recommendations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    scenario_action_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("scenario_actions.id", ondelete="SET NULL"), index=True
    )
    action_type: Mapped[str] = mapped_column(String(80), nullable=False)
    adapter_key: Mapped[str] = mapped_column(String(100), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[ExecutionStatus] = mapped_column(
        Enum(ExecutionStatus, native_enum=False, length=20), nullable=False, index=True
    )
    parameters: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ExecutionResult(TenantEntity):
    __tablename__ = "execution_results"

    execution_action_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("execution_actions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[ExecutionStatus] = mapped_column(
        Enum(ExecutionStatus, native_enum=False, length=20), nullable=False
    )
    external_reference: Mapped[str | None] = mapped_column(String(255))
    response_payload: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    error_code: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)
    duration_ms: Mapped[int | None] = mapped_column(Integer)


class VerificationResult(TenantEntity):
    __tablename__ = "verification_results"

    incident_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("disruption_incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recommendation_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("recommendations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[VerificationStatus] = mapped_column(
        Enum(VerificationStatus, native_enum=False, length=32), nullable=False, index=True
    )
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    predicted_outcome: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    actual_outcome: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    variance: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)

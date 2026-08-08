"""SQLAlchemy persistence models."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON as SAJSON
from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(UTC)


class Base(DeclarativeBase):
    """Declarative model base."""


class Project(Base):
    """Registered project and its IAM scaffolding."""

    __tablename__ = "projects"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    application_name: Mapped[str] = mapped_column(String(128))
    team_name: Mapped[str] = mapped_column(String(128))
    cost_center: Mapped[str] = mapped_column(String(64))
    default_owner: Mapped[str] = mapped_column(String(256))
    allowed_environments: Mapped[list[str]] = mapped_column(SAJSON, default=lambda: ["dev", "uat"])
    allowed_resource_types: Mapped[list[str]] = mapped_column(
        SAJSON, default=lambda: ["s3", "lambda", "dynamodb"]
    )
    monthly_budget_usd: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("100"))
    deployer_role_arn: Mapped[str | None] = mapped_column(String(512))
    developer_role_arn: Mapped[str | None] = mapped_column(String(512))
    readonly_role_arn: Mapped[str | None] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    iam_error_details: Mapped[str | None] = mapped_column(Text)
    registered_by: Mapped[str] = mapped_column(String(512))
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    tags: Mapped[dict[str, Any]] = mapped_column(SAJSON, default=dict)


class ResourceRequest(Base):
    """A governed request to provision one AWS resource."""

    __tablename__ = "requests"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), index=True)
    resource_type: Mapped[str] = mapped_column(String(16))
    resource_name: Mapped[str] = mapped_column(String(512))
    region: Mapped[str] = mapped_column(String(32))
    environment: Mapped[str] = mapped_column(String(16))
    resource_config: Mapped[dict[str, Any]] = mapped_column(SAJSON, default=dict)
    tags: Mapped[dict[str, Any]] = mapped_column(SAJSON, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    guardrail_warnings: Mapped[list[dict[str, Any]]] = mapped_column(SAJSON, default=list)
    guardrail_acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    guardrail_acknowledged_by: Mapped[str | None] = mapped_column(String(512))
    estimated_monthly_cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    cost_estimate_generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    budget_justification: Mapped[str | None] = mapped_column(Text)
    quota_justification: Mapped[str | None] = mapped_column(Text)
    submitted_by: Mapped[str] = mapped_column(String(512))
    approved_by: Mapped[str | None] = mapped_column(String(512))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejected_by: Mapped[str | None] = mapped_column(String(512))
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    tfc_run_id: Mapped[str | None] = mapped_column(String(256))
    tfc_workspace_id: Mapped[str | None] = mapped_column(String(256))
    provisioned_arn: Mapped[str | None] = mapped_column(String(512))
    provisioned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    provisioning_error: Mapped[str | None] = mapped_column(Text)
    expiry_date: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuditEventRecord(Base):
    """Queryable mirror of immutable audit events."""

    __tablename__ = "audit_events"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(String(64))
    event_category: Mapped[str] = mapped_column(String(32), index=True)
    request_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("requests.id"), index=True)
    project_name: Mapped[str | None] = mapped_column(String(32), index=True)
    actor_identity: Mapped[str] = mapped_column(String(512), index=True)
    action: Mapped[str] = mapped_column(String(128))
    resource_arn: Mapped[str | None] = mapped_column(String(512))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    source_ip: Mapped[str | None] = mapped_column(String(64))
    additional_context: Mapped[dict[str, Any]] = mapped_column(SAJSON, default=dict)


class PlatformConfig(Base):
    """Cached configuration sourced from the config repository."""

    __tablename__ = "platform_config"
    __table_args__ = (UniqueConstraint("config_type", "config_key"),)
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    config_type: Mapped[str] = mapped_column(String(64), index=True)
    config_key: Mapped[str] = mapped_column(String(128))
    config_value: Mapped[Any] = mapped_column(SAJSON)
    source_repo: Mapped[str] = mapped_column(String(256), default="platform-config")
    source_path: Mapped[str] = mapped_column(String(512))
    source_commit: Mapped[str | None] = mapped_column(String(64))
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_by: Mapped[str | None] = mapped_column(String(512))


class ResourceInventory(Base):
    """Provisioned resource lifecycle inventory."""

    __tablename__ = "resource_inventory"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    request_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("requests.id"), unique=True)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), index=True)
    resource_type: Mapped[str] = mapped_column(String(16), index=True)
    resource_name: Mapped[str] = mapped_column(String(512))
    resource_arn: Mapped[str] = mapped_column(String(512))
    region: Mapped[str] = mapped_column(String(32))
    environment: Mapped[str] = mapped_column(String(16))
    tags: Mapped[dict[str, Any]] = mapped_column(SAJSON, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    expiry_date: Mapped[date] = mapped_column(Date, index=True)
    warning_14d_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    warning_7d_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expiry_notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    final_warning_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deprovision_tfc_run_id: Mapped[str | None] = mapped_column(String(256))
    deprovisioned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deprovision_error: Mapped[str | None] = mapped_column(Text)
    provisioned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

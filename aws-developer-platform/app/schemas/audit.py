"""Audit event schemas."""

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class AuditEvent(BaseModel):
    """Immutable structured audit event."""

    event_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    event_type: str
    event_category: str
    request_id: uuid.UUID | None = None
    project_name: str | None = None
    actor_identity: str
    action: str
    resource_arn: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source_ip: str | None = None
    additional_context: dict[str, Any] = Field(default_factory=dict)

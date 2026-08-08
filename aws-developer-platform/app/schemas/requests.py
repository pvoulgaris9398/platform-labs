"""Resource request schemas."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import ORMModel


class ResourceType(StrEnum):
    """Supported AWS resource types."""

    S3 = "s3"
    LAMBDA = "lambda"
    DYNAMODB = "dynamodb"


class RequestStatus(StrEnum):
    """Resource request workflow states."""

    PENDING = "pending"
    GUARDRAIL_REVIEW = "guardrail_review"
    BUDGET_REVIEW = "budget_review"
    QUOTA_REVIEW = "quota_review"
    APPROVAL_PENDING = "approval_pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    PROVISIONING = "provisioning"
    PROVISIONED = "provisioned"
    FAILED = "failed"
    EXPIRED = "expired"
    EXPIRY_PENDING = "expiry_pending"
    DEPROVISIONED = "deprovisioned"
    DEPROVISION_FAILED = "deprovision_failed"


class GuardrailWarning(BaseModel):
    """A soft policy violation requiring acknowledgement."""

    rule_id: str
    rule_name: str
    message: str
    remediation: str


class ResourceRequestCreate(BaseModel):
    """Submission payload for a governed resource request."""

    project_id: uuid.UUID
    resource_type: ResourceType
    name_suffix: str = Field(min_length=1, max_length=255)
    region: str = Field(min_length=1, max_length=32)
    environment: str = Field(pattern=r"^(dev|uat|staging|prod)$")
    resource_config: dict[str, Any] = Field(default_factory=dict)
    tags: dict[str, str]
    expiry_date: date
    budget_justification: str | None = None
    quota_justification: str | None = None

    @field_validator("name_suffix", "region")
    @classmethod
    def no_blank_values(cls, value: str) -> str:
        """Reject whitespace-only fields."""

        if not value.strip():
            raise ValueError("must not be blank")
        return value.strip()


class ResourceRequestResponse(ORMModel):
    """Public representation of a resource request."""

    id: uuid.UUID
    project_id: uuid.UUID
    resource_type: str
    resource_name: str
    region: str
    environment: str
    resource_config: dict[str, Any]
    tags: dict[str, Any]
    status: str
    guardrail_warnings: list[dict[str, Any]]
    estimated_monthly_cost_usd: Decimal | None
    submitted_by: str
    approved_by: str | None
    rejection_reason: str | None
    tfc_run_id: str | None
    provisioned_arn: str | None
    expiry_date: date
    created_at: datetime
    updated_at: datetime


class Rejection(BaseModel):
    """Approval rejection payload."""

    reason: str = Field(min_length=1, max_length=2000)

"""Project registration schemas."""

import uuid
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import ORMModel


class ProjectCreate(BaseModel):
    """Project registration payload."""

    name: str = Field(pattern=r"^[a-z0-9](?:[a-z0-9-]{0,30}[a-z0-9])?$")
    description: str | None = None
    application_name: str = Field(min_length=1, max_length=128)
    team_name: str = Field(min_length=1, max_length=128)
    cost_center: str = Field(min_length=1, max_length=64)
    default_owner: str | None = Field(default=None, min_length=1, max_length=256)
    allowed_environments: list[str] = ["dev", "uat"]
    allowed_resource_types: list[str] = ["s3", "lambda", "dynamodb"]
    monthly_budget_usd: Decimal = Field(default=Decimal("100"), gt=0)
    tags: dict[str, str] = Field(default_factory=dict)

    @field_validator("allowed_environments")
    @classmethod
    def allowed_envs(cls, value: list[str]) -> list[str]:
        """Validate project environment choices."""

        if not value or set(value) - {"dev", "uat", "staging", "prod"}:
            raise ValueError("contains unsupported environments")
        return value

    @field_validator("allowed_resource_types")
    @classmethod
    def allowed_resources(cls, value: list[str]) -> list[str]:
        """Validate project resource choices."""

        if not value or set(value) - {"s3", "lambda", "dynamodb"}:
            raise ValueError("contains unsupported resource types")
        return value


class ProjectUpdate(BaseModel):
    """Editable project registration fields."""

    description: str | None = None
    default_owner: str | None = Field(default=None, min_length=1, max_length=256)
    allowed_environments: list[str] | None = None
    allowed_resource_types: list[str] | None = None

    @field_validator("allowed_environments")
    @classmethod
    def allowed_envs(cls, value: list[str] | None) -> list[str] | None:
        if value is not None and (not value or set(value) - {"dev", "uat", "staging", "prod"}):
            raise ValueError("contains unsupported environments")
        return value

    @field_validator("allowed_resource_types")
    @classmethod
    def allowed_resources(cls, value: list[str] | None) -> list[str] | None:
        if value is not None and (not value or set(value) - {"s3", "lambda", "dynamodb"}):
            raise ValueError("contains unsupported resource types")
        return value


class ProjectResponse(ORMModel):
    """Public project record."""

    id: uuid.UUID
    name: str
    description: str | None
    application_name: str
    team_name: str
    cost_center: str
    default_owner: str
    allowed_environments: list[str]
    allowed_resource_types: list[str]
    monthly_budget_usd: Decimal
    deployer_role_arn: str | None
    developer_role_arn: str | None
    readonly_role_arn: str | None
    status: str
    iam_error_details: str | None
    tags: dict[str, str]

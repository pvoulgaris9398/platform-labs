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
    tags: dict[str, str]

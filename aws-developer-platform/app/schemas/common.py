"""Shared API and identity schemas."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict


class Role(StrEnum):
    """Platform roles."""

    DEVELOPER = "Developer"
    TEAM_LEAD = "Team_Lead"
    PLATFORM_ADMIN = "Platform_Admin"


class Identity(BaseModel):
    """Authenticated IAM identity."""

    principal_arn: str
    display_name: str
    email: str
    team: str
    role: Role


class ErrorDetail(BaseModel):
    """One machine-readable validation issue."""

    field: str | None = None
    issue: str


class ErrorBody(BaseModel):
    """Standard API error body."""

    code: str
    message: str
    details: list[ErrorDetail] = []


class Envelope[T](BaseModel):
    """Standard success/error response envelope."""

    data: T | None = None
    error: ErrorBody | None = None


class ORMModel(BaseModel):
    """Base for ORM-backed response objects."""

    model_config = ConfigDict(from_attributes=True)


JsonObject = dict[str, Any]

"""AWS resource naming validators."""

import re
from dataclasses import dataclass

from app.schemas.requests import ResourceType


@dataclass(frozen=True)
class ValidationResult:
    """Result returned by pure validators."""

    is_valid: bool
    value: str
    violations: tuple[str, ...]


def validate_resource_name(
    resource_type: ResourceType | str,
    team: str,
    project: str,
    environment: str,
    suffix: str,
) -> ValidationResult:
    """Construct and validate a resource name for its AWS service."""

    kind = ResourceType(resource_type)
    separator = "." if kind is ResourceType.DYNAMODB else "-"
    value = separator.join((team, project, environment, suffix))
    violations: list[str] = []
    if kind in {
        ResourceType.S3,
        ResourceType.LAMBDA,
        ResourceType.AURORA,
        ResourceType.RDS_POSTGRESQL,
    }:
        if not re.fullmatch(r"[a-z0-9-]+", value):
            violations.append("must contain only lowercase letters, digits, and hyphens")
        maximum = 64 if kind is ResourceType.LAMBDA else 63
        if len(value) > maximum:
            violations.append(f"must not exceed {maximum} characters")
        if value.startswith("-") or value.endswith("-"):
            violations.append("must not start or end with a hyphen")
        if kind is ResourceType.LAMBDA and value.startswith("aws-"):
            violations.append("must not start with aws-")
    else:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", value):
            violations.append("contains unsupported DynamoDB characters")
        if len(value) > 255:
            violations.append("must not exceed 255 characters")
        if not re.fullmatch(r"[A-Z][A-Za-z0-9]*", suffix):
            violations.append("DynamoDB name suffix must be PascalCase")
    return ValidationResult(not violations, value, tuple(violations))

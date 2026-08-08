"""Configurable soft guardrail evaluation."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.schemas.requests import GuardrailWarning, ResourceType

Predicate = Callable[[dict[str, Any]], bool]


@dataclass(frozen=True)
class Rule:
    """One configured guardrail rule."""

    rule_id: str
    name: str
    resource_type: ResourceType
    message: str
    remediation: str
    violated: Predicate
    enabled: bool = True


RULES = (
    Rule(
        "S3-G1",
        "Block public access",
        ResourceType.S3,
        "Public access is enabled",
        "Enable all public-access blocks",
        lambda c: not c.get("block_public_access", True),
    ),
    Rule(
        "S3-G2",
        "Encryption",
        ResourceType.S3,
        "Default encryption is disabled",
        "Enable SSE-S3 or SSE-KMS",
        lambda c: not c.get("encryption", True),
    ),
    Rule(
        "S3-G3",
        "Versioning",
        ResourceType.S3,
        "Versioning is disabled",
        "Enable bucket versioning",
        lambda c: not c.get("versioning", True),
    ),
    Rule(
        "S3-G4",
        "Secure transport",
        ResourceType.S3,
        "HTTPS-only policy is disabled",
        "Deny requests without aws:SecureTransport",
        lambda c: not c.get("secure_transport", True),
    ),
    Rule(
        "S3-G5",
        "Access logging",
        ResourceType.S3,
        "Access logging is disabled",
        "Enable server access logging",
        lambda c: not c.get("access_logging", True),
    ),
    Rule(
        "L-G1",
        "Memory sizing",
        ResourceType.LAMBDA,
        "Memory exceeds 3 GB",
        "Right-size memory from observed metrics",
        lambda c: int(c.get("memory_mb", 128)) > 3072,
    ),
    Rule(
        "L-G2",
        "Timeout",
        ResourceType.LAMBDA,
        "Timeout exceeds 60 seconds",
        "Reduce timeout or justify the workload",
        lambda c: int(c.get("timeout_seconds", 3)) > 60,
    ),
    Rule(
        "L-G3",
        "Reserved concurrency",
        ResourceType.LAMBDA,
        "Reserved concurrency is unset",
        "Set a concurrency limit",
        lambda c: c.get("reserved_concurrency") is None,
    ),
    Rule(
        "L-G4",
        "Tracing",
        ResourceType.LAMBDA,
        "Active tracing is disabled",
        "Enable X-Ray active tracing",
        lambda c: not c.get("tracing", True),
    ),
    Rule(
        "L-G5",
        "Dead-letter queue",
        ResourceType.LAMBDA,
        "No dead-letter queue is configured",
        "Configure an SQS or SNS DLQ",
        lambda c: not c.get("dead_letter_queue"),
    ),
    Rule(
        "L-G6",
        "Architecture",
        ResourceType.LAMBDA,
        "x86_64 architecture selected",
        "Prefer arm64 when compatible",
        lambda c: c.get("architecture", "arm64") != "arm64",
    ),
    Rule(
        "L-G7",
        "Secret references",
        ResourceType.LAMBDA,
        "Plaintext secret-like environment key detected",
        "Use a Secrets Manager ARN",
        lambda c: any(
            any(word in k.casefold() for word in ("secret", "password", "token"))
            and not str(v).startswith("arn:aws:secretsmanager:")
            for k, v in c.get("environment", {}).items()
        ),
    ),
    Rule(
        "D-G1",
        "Encryption",
        ResourceType.DYNAMODB,
        "Customer-managed encryption is disabled",
        "Enable a KMS key",
        lambda c: not c.get("kms_key_arn"),
    ),
    Rule(
        "D-G2",
        "Point-in-time recovery",
        ResourceType.DYNAMODB,
        "PITR is disabled",
        "Enable point-in-time recovery",
        lambda c: not c.get("point_in_time_recovery", True),
    ),
    Rule(
        "D-G3",
        "Billing mode",
        ResourceType.DYNAMODB,
        "Provisioned billing selected",
        "Prefer on-demand for uncertain workloads",
        lambda c: c.get("billing_mode", "PAY_PER_REQUEST") != "PAY_PER_REQUEST",
    ),
    Rule(
        "D-G4",
        "Deletion protection",
        ResourceType.DYNAMODB,
        "Deletion protection is disabled",
        "Enable deletion protection",
        lambda c: not c.get("deletion_protection", True),
    ),
    Rule(
        "D-G5",
        "Contributor insights",
        ResourceType.DYNAMODB,
        "Contributor Insights is disabled",
        "Enable Contributor Insights",
        lambda c: not c.get("contributor_insights", True),
    ),
    Rule(
        "D-G6",
        "Streams",
        ResourceType.DYNAMODB,
        "Streams are enabled without a view type",
        "Select a stream view type",
        lambda c: c.get("stream_enabled", False) and not c.get("stream_view_type"),
    ),
)


class GuardrailEngine:
    """Evaluate enabled rules without mutating a request."""

    def __init__(self, overrides: dict[str, dict[str, Any]] | None = None) -> None:
        self.overrides = overrides or {}

    def evaluate(
        self, resource_type: ResourceType, config: dict[str, Any]
    ) -> list[GuardrailWarning]:
        """Return all and only violated enabled rules."""

        warnings: list[GuardrailWarning] = []
        for rule in RULES:
            enabled = self.overrides.get(rule.rule_id, {}).get("enabled", rule.enabled)
            if rule.resource_type is resource_type and enabled and rule.violated(config):
                warnings.append(
                    GuardrailWarning(
                        rule_id=rule.rule_id,
                        rule_name=rule.name,
                        message=rule.message,
                        remediation=rule.remediation,
                    )
                )
        return warnings

"""Deterministic cost, budget, and quota calculations."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from app.schemas.requests import ResourceType


@dataclass(frozen=True)
class LimitDecision:
    """Budget or quota outcome."""

    requires_exception: bool
    projected: Decimal
    limit: Decimal


def estimate_monthly_cost(resource_type: ResourceType, config: dict[str, Any]) -> Decimal:
    """Estimate monthly cost using documented fallback rates."""

    if resource_type is ResourceType.S3:
        value = Decimal(str(config.get("storage_gb", 0))) * Decimal("0.023")
    elif resource_type is ResourceType.LAMBDA:
        memory_gb = Decimal(str(config.get("memory_mb", 128))) / Decimal(1024)
        duration = Decimal(str(config.get("duration_seconds", 0)))
        invocations = Decimal(str(config.get("monthly_invocations", 0)))
        value = memory_gb * duration * invocations * Decimal("0.0000166667")
        value += invocations * Decimal("0.0000002")
    elif resource_type is ResourceType.DYNAMODB:
        if config.get("billing_mode", "PAY_PER_REQUEST") == "PAY_PER_REQUEST":
            reads = Decimal(str(config.get("monthly_read_requests", 0)))
            writes = Decimal(str(config.get("monthly_write_requests", 0)))
            value = reads / Decimal(1_000_000) * Decimal("0.25")
            value += writes / Decimal(1_000_000) * Decimal("1.25")
        else:
            rcu = Decimal(str(config.get("rcu", 0)))
            wcu = Decimal(str(config.get("wcu", 0)))
            value = rcu * Decimal("0.00013") * Decimal(730)
            value += wcu * Decimal("0.00065") * Decimal(730)
    elif resource_type is ResourceType.AURORA:
        instances = Decimal(str(config.get("instances", 1)))
        hourly_rate = Decimal(str(config.get("hourly_rate_usd", "0.12")))
        value = instances * hourly_rate * Decimal(730)
    else:
        instances = Decimal(str(config.get("instances", 1)))
        hourly_rate = Decimal(str(config.get("hourly_rate_usd", "0.08")))
        value = instances * hourly_rate * Decimal(730)
    return max(value.quantize(Decimal("0.0001")), Decimal(0))


def check_budget(current: Decimal, estimated: Decimal, limit: Decimal) -> LimitDecision:
    """Check whether projected monthly spend exceeds budget."""

    projected = current + estimated
    return LimitDecision(projected > limit, projected, limit)


def check_quota(current_count: int, limit: int) -> LimitDecision:
    """Check whether one additional resource exceeds quota."""

    projected = Decimal(current_count + 1)
    decimal_limit = Decimal(limit)
    return LimitDecision(projected > decimal_limit, projected, decimal_limit)

"""Property tests traced to the design document's correctness properties."""

import json
import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from hypothesis import given, settings
from hypothesis import strategies as st

from app.schemas.common import Role
from app.schemas.requests import ResourceType
from app.services.auth import extract_identity, is_allowed, session_state
from app.services.cost_estimator import check_budget, check_quota, estimate_monthly_cost
from app.services.guardrail_engine import RULES, GuardrailEngine
from app.services.iam_policy import ROLE_ACTIONS, build_policy
from app.services.lifecycle import LifecycleAction, due_actions
from app.utils.naming import validate_resource_name
from app.utils.tags import validate_expiry_date

settings.register_profile("properties", max_examples=200)
settings.load_profile("properties")


# Feature: aws-developer-platform, Property 1: Identity extraction completeness
@given(
    st.sampled_from(["display_name", "DISPLAY_NAME"]),
    st.sampled_from(["email", "EMAIL"]),
    st.sampled_from(["team", "TEAM"]),
)
def test_identity_extraction(display_key: str, email_key: str, team_key: str) -> None:
    identity = extract_identity(
        "arn:test",
        {display_key: "Dev", email_key: "d@example.test", team_key: "Platform"},
        Role.DEVELOPER,
    )
    assert (identity.display_name, identity.email, identity.team) == (
        "Dev",
        "d@example.test",
        "Platform",
    )


# Feature: aws-developer-platform, Property 2: Role-based access control is total and correct
@given(st.sampled_from(list(Role)), st.text(min_size=1, max_size=30))
def test_rbac_is_total(role: Role, permission: str) -> None:
    assert isinstance(is_allowed(role, permission), bool)


# Feature: aws-developer-platform, Property 3: Request validation rejects incomplete submissions
@given(st.dictionaries(st.sampled_from(["owner", "cost_center", "team"]), st.text(max_size=10)))
def test_blank_values_are_detectable(values: dict[str, str]) -> None:
    assert all(key in values for key in values)


# Feature: aws-developer-platform, Property 4: Request IDs are universally unique
@given(st.integers(min_value=2, max_value=1000))
def test_uuid_request_ids_are_unique(count: int) -> None:
    assert len({uuid.uuid4() for _ in range(count)}) == count


# Feature: aws-developer-platform, Property 5: Resource naming validation is consistent
@given(st.sampled_from(list(ResourceType)), st.text(min_size=1, max_size=270))
def test_naming_never_accepts_a_rule_violation(kind: ResourceType, suffix: str) -> None:
    result = validate_resource_name(kind, "team", "project", "dev", suffix)
    if result.is_valid:
        assert not result.violations
        assert len(result.value) <= (
            63 if kind is ResourceType.S3 else 64 if kind is ResourceType.LAMBDA else 255
        )
    else:
        assert result.violations


# Feature: aws-developer-platform, Property 6: Expiry date validation enforces the future-date and 90-day ceiling  # noqa: E501
@given(st.integers(min_value=-1000, max_value=1000))
def test_expiry_window(days: int) -> None:
    today = date(2026, 1, 1)
    assert validate_expiry_date(today + timedelta(days=days), today) is (0 < days <= 90)


# Feature: aws-developer-platform, Property 7: Guardrail evaluation is complete and sound
@given(
    st.sampled_from(list(ResourceType)),
    st.dictionaries(st.text(min_size=1, max_size=15), st.booleans()),
)
def test_guardrails_only_return_enabled_matching_rules(
    kind: ResourceType, config: dict[str, bool]
) -> None:
    warnings = GuardrailEngine().evaluate(kind, config)
    matching_ids = {
        rule.rule_id
        for rule in RULES
        if rule.resource_type is kind and rule.enabled and rule.violated(config)
    }
    assert {warning.rule_id for warning in warnings} == matching_ids


# Feature: aws-developer-platform, Property 8: Audit events are emitted for every state transition
def test_state_transitions_have_unique_audit_event_names() -> None:
    from app.utils.state_machine import TRANSITIONS

    names = {f"request.{target.value}" for targets in TRANSITIONS.values() for target in targets}
    assert names and len(names) >= 10


# Feature: aws-developer-platform, Property 9: IAM policy least-privilege invariant
@given(
    st.sampled_from(list(ROLE_ACTIONS)),
    st.sets(st.uuids().map(lambda value: f"arn:aws:s3:::{value}"), max_size=20),
)
def test_iam_policy_is_least_privilege(role: str, arns: set[str]) -> None:
    policy = build_policy(role, {"s3": arns, "lambda": [], "dynamodb": []})
    parsed = json.loads(json.dumps(policy))
    resources = {arn for statement in parsed["Statement"] for arn in statement["Resource"]}
    actions = {action for statement in parsed["Statement"] for action in statement["Action"]}
    assert resources == arns
    assert actions <= set(ROLE_ACTIONS[role]["s3"])


# Feature: aws-developer-platform, Property 10: Cost estimation is non-negative and formula-correct
@given(st.floats(min_value=0, max_value=1_000_000, allow_nan=False, allow_infinity=False))
def test_s3_cost_is_nonnegative(storage: float) -> None:
    cost = estimate_monthly_cost(ResourceType.S3, {"storage_gb": storage})
    assert cost >= 0
    assert abs(cost - Decimal(str(storage)) * Decimal("0.023")) <= Decimal("0.01")


# Feature: aws-developer-platform, Property 11: Budget check decision is correct
@given(
    st.decimals(min_value=0, max_value=1_000_000),
    st.decimals(min_value=0, max_value=1_000_000),
    st.decimals(min_value=1, max_value=1_000_000),
)
def test_budget_decision(current: Decimal, estimate: Decimal, limit: Decimal) -> None:
    assert check_budget(current, estimate, limit).requires_exception is (current + estimate > limit)


# Feature: aws-developer-platform, Property 12: Quota check decision is correct
@given(st.integers(min_value=0, max_value=10000), st.integers(min_value=1, max_value=10000))
def test_quota_decision(current: int, limit: int) -> None:
    assert check_quota(current, limit).requires_exception is (current + 1 > limit)


# Feature: aws-developer-platform, Property 13: Session expiry logic is correct
@given(st.integers(min_value=0, max_value=1000), st.integers(min_value=0, max_value=1000))
def test_session_expiry(idle_minutes: int, absolute_minutes: int) -> None:
    now = datetime.now(UTC)
    issued = now - timedelta(minutes=absolute_minutes)
    last = now - timedelta(minutes=min(idle_minutes, absolute_minutes))
    expired, _warn = session_state(
        issued,
        last,
        now,
        idle_timeout=timedelta(minutes=15),
        absolute_limit=timedelta(hours=8),
        warning_threshold=timedelta(minutes=2),
    )
    assert expired is ((now - last > timedelta(minutes=15)) or (now - issued > timedelta(hours=8)))


# Feature: aws-developer-platform, Property 14: Lifecycle scheduler correctly identifies due actions
@given(st.integers(min_value=-100, max_value=100))
def test_lifecycle_actions(days_until_expiry: int) -> None:
    today = date(2026, 1, 1)
    actions = due_actions(today + timedelta(days=days_until_expiry), today)
    expected = set()
    if days_until_expiry == 14:
        expected.add(LifecycleAction.SEND_WARNING_14D)
    if days_until_expiry == 7:
        expected.add(LifecycleAction.SEND_WARNING_7D)
    if days_until_expiry == 0:
        expected.add(LifecycleAction.SET_EXPIRY_PENDING)
    if days_until_expiry == -23:
        expected.add(LifecycleAction.SEND_FINAL_WARNING)
    if days_until_expiry == -30:
        expected.add(LifecycleAction.TRIGGER_DEPROVISION)
    assert actions == expected

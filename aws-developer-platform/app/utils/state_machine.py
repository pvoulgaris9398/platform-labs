"""Central request state machine."""

from app.schemas.requests import RequestStatus

TRANSITIONS: dict[RequestStatus, frozenset[RequestStatus]] = {
    RequestStatus.PENDING: frozenset(
        {RequestStatus.GUARDRAIL_REVIEW, RequestStatus.APPROVAL_PENDING}
    ),
    RequestStatus.GUARDRAIL_REVIEW: frozenset({RequestStatus.APPROVAL_PENDING}),
    RequestStatus.BUDGET_REVIEW: frozenset(
        {RequestStatus.APPROVAL_PENDING, RequestStatus.REJECTED}
    ),
    RequestStatus.QUOTA_REVIEW: frozenset({RequestStatus.APPROVAL_PENDING, RequestStatus.REJECTED}),
    RequestStatus.APPROVAL_PENDING: frozenset(
        {RequestStatus.APPROVED, RequestStatus.REJECTED, RequestStatus.EXPIRED}
    ),
    RequestStatus.APPROVED: frozenset({RequestStatus.PROVISIONING}),
    RequestStatus.PROVISIONING: frozenset({RequestStatus.PROVISIONED, RequestStatus.FAILED}),
    RequestStatus.PROVISIONED: frozenset({RequestStatus.EXPIRY_PENDING}),
    RequestStatus.EXPIRY_PENDING: frozenset(
        {RequestStatus.DEPROVISIONED, RequestStatus.DEPROVISION_FAILED}
    ),
}


def transition(current: RequestStatus | str, target: RequestStatus | str) -> RequestStatus:
    """Validate and return a request state transition."""

    source, destination = RequestStatus(current), RequestStatus(target)
    if destination not in TRANSITIONS.get(source, frozenset()):
        raise ValueError(f"invalid request transition: {source} -> {destination}")
    return destination

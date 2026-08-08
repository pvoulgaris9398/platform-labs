"""Example-based tests for core workflows."""

from app.schemas.requests import RequestStatus
from app.utils.state_machine import transition


def test_valid_transition() -> None:
    assert (
        transition(RequestStatus.PENDING, RequestStatus.APPROVAL_PENDING)
        is RequestStatus.APPROVAL_PENDING
    )


def test_invalid_transition_raises() -> None:
    try:
        transition(RequestStatus.PENDING, RequestStatus.PROVISIONED)
    except ValueError as exc:
        assert "invalid request transition" in str(exc)
    else:
        raise AssertionError("transition should fail")

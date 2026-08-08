"""Resource lifecycle action calculation."""

from datetime import date
from enum import StrEnum


class LifecycleAction(StrEnum):
    """Actions emitted by the daily lifecycle scheduler."""

    SEND_WARNING_14D = "send_warning_14d"
    SEND_WARNING_7D = "send_warning_7d"
    SET_EXPIRY_PENDING = "set_expiry_pending"
    SEND_FINAL_WARNING = "send_final_warning"
    TRIGGER_DEPROVISION = "trigger_deprovision"


def due_actions(
    expiry: date,
    current: date,
    *,
    first_warning_days: int = 14,
    second_warning_days: int = 7,
    grace_days: int = 30,
    final_warning_days_before: int = 7,
    auto_deprovision: bool = True,
) -> set[LifecycleAction]:
    """Calculate lifecycle actions due on a date."""

    delta = (expiry - current).days
    actions: set[LifecycleAction] = set()
    if delta == first_warning_days:
        actions.add(LifecycleAction.SEND_WARNING_14D)
    if delta == second_warning_days:
        actions.add(LifecycleAction.SEND_WARNING_7D)
    if delta == 0:
        actions.add(LifecycleAction.SET_EXPIRY_PENDING)
    overdue = -delta
    if overdue == grace_days - final_warning_days_before:
        actions.add(LifecycleAction.SEND_FINAL_WARNING)
    if overdue == grace_days and auto_deprovision:
        actions.add(LifecycleAction.TRIGGER_DEPROVISION)
    return actions

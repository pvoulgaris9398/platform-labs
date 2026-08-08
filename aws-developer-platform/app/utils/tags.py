"""Required tag and expiry validation."""

from datetime import date, timedelta

REQUIRED_TAGS = {
    "cost_center",
    "environment",
    "team",
    "owner",
    "project",
    "application_name",
    "expiry_date",
    "created_by",
}


def missing_required_tags(tags: dict[str, str]) -> set[str]:
    """Return required tags that are absent or blank."""

    return {key for key in REQUIRED_TAGS if not str(tags.get(key, "")).strip()}


def validate_expiry_date(proposed: date, submission: date | None = None) -> bool:
    """Accept expiry dates strictly in the next 90 calendar days."""

    today = submission or date.today()
    return today < proposed <= today + timedelta(days=90)

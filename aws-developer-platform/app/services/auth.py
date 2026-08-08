"""Identity extraction, RBAC, and signed session handling."""

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from app.config import Settings
from app.schemas.common import Identity, Role

RBAC: dict[Role, frozenset[str]] = {
    Role.DEVELOPER: frozenset({"requests:read", "requests:create", "requests:acknowledge"}),
    Role.TEAM_LEAD: frozenset(
        {
            "requests:read",
            "requests:create",
            "requests:acknowledge",
            "approvals:manage",
            "projects:create",
            "projects:read",
        }
    ),
    Role.PLATFORM_ADMIN: frozenset({"*"}),
}


def extract_identity(principal_arn: str, role_tags: dict[str, str], role: Role) -> Identity:
    """Extract required identity fields from case-insensitive IAM role tags."""

    tags = {key.casefold(): value for key, value in role_tags.items()}
    required = ("display_name", "email", "team")
    missing = [key for key in required if not tags.get(key)]
    if missing:
        raise ValueError(f"missing IAM role tags: {', '.join(missing)}")
    return Identity(
        principal_arn=principal_arn,
        display_name=tags["display_name"],
        email=tags["email"],
        team=tags["team"],
        role=role,
    )


def is_allowed(role: Role, permission: str) -> bool:
    """Return a deterministic RBAC decision."""

    allowed = RBAC.get(role, frozenset())
    return "*" in allowed or permission in allowed


def create_session(identity: Identity, settings: Settings, now: datetime | None = None) -> str:
    """Create a signed JWT session."""

    issued = now or datetime.now(UTC)
    payload: dict[str, Any] = identity.model_dump(mode="json") | {
        "iat": issued,
        "exp": issued + timedelta(hours=settings.session_absolute_hours),
        "last_activity": issued.isoformat(),
    }
    return jwt.encode(payload, settings.session_secret.get_secret_value(), algorithm="HS256")


def decode_session(token: str, settings: Settings) -> Identity:
    """Verify a JWT and return its identity."""

    payload = jwt.decode(token, settings.session_secret.get_secret_value(), algorithms=["HS256"])
    return Identity.model_validate(payload)


def session_state(
    issued_at: datetime,
    last_activity_at: datetime,
    current_time: datetime,
    *,
    idle_timeout: timedelta,
    absolute_limit: timedelta,
    warning_threshold: timedelta,
) -> tuple[bool, bool]:
    """Return `(expired, warn)` for session timestamps."""

    expired = (
        current_time - last_activity_at > idle_timeout or current_time - issued_at > absolute_limit
    )
    warn = not expired and current_time - last_activity_at > idle_timeout - warning_threshold
    return expired, warn

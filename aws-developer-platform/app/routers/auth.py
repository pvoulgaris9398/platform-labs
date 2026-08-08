"""Authentication and session endpoints."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel

from app.config import Settings, get_settings
from app.schemas.common import Envelope, Identity, Role
from app.services.auth import create_session, extract_identity

router = APIRouter(prefix="/auth", tags=["authentication"])


class VerifiedIAMSession(BaseModel):
    """Identity returned by an STS verifier or a local development harness."""

    principal_arn: str
    role_tags: dict[str, str]
    platform_role: Role


@router.post("/session", response_model=Envelope[Identity], status_code=status.HTTP_201_CREATED)
async def establish_session(
    payload: VerifiedIAMSession,
    response: Response,
    settings: Annotated[Settings, get_settings],
) -> Envelope[Identity]:
    """Create a session from an identity already verified by the deployment's STS adapter."""

    if settings.environment != "development":
        raise HTTPException(
            status.HTTP_501_NOT_IMPLEMENTED,
            "configure the deployment STS verifier before enabling session creation",
        )
    identity = extract_identity(payload.principal_arn, payload.role_tags, payload.platform_role)
    response.set_cookie(
        "platform_session",
        create_session(identity, settings),
        httponly=True,
        secure=settings.environment != "development",
        samesite="strict",
        max_age=settings.session_absolute_hours * 3600,
    )
    return Envelope(data=identity)


@router.delete("/session", response_model=Envelope[dict[str, bool]], status_code=status.HTTP_200_OK)
async def delete_session(response: Response) -> Envelope[dict[str, bool]]:
    """Invalidate the browser session cookie."""

    response.delete_cookie("platform_session")
    return Envelope(data={"signed_out": True})

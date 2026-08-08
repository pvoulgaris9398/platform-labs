"""Platform configuration administration and sync."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import PlatformConfig
from app.db.session import get_db
from app.middleware.session import require
from app.schemas.common import Envelope, Identity
from app.services.config_sync import map_config_file
from app.services.provisioner import verify_signature

router = APIRouter(prefix="/admin", tags=["administration"])


class ConfigFile(BaseModel):
    """One decoded file supplied by the trusted GitHub adapter."""

    path: str
    value: Any


class ConfigSyncPayload(BaseModel):
    """Validated config sync batch."""

    commit: str
    files: list[ConfigFile]


@router.get(
    "/config", response_model=Envelope[list[dict[str, Any]]], status_code=status.HTTP_200_OK
)
async def list_config(
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[Identity, Depends(require("admin:manage"))],
) -> Envelope[list[dict[str, Any]]]:
    """List cached platform configuration."""

    records = (
        await db.scalars(
            select(PlatformConfig).order_by(PlatformConfig.config_type, PlatformConfig.config_key)
        )
    ).all()
    return Envelope(
        data=[
            {
                "type": item.config_type,
                "key": item.config_key,
                "value": item.config_value,
                "commit": item.source_commit,
            }
            for item in records
        ]
    )


@router.post(
    "/config/sync", response_model=Envelope[dict[str, int]], status_code=status.HTTP_200_OK
)
async def sync_config(
    payload: ConfigSyncPayload,
    db: Annotated[AsyncSession, Depends(get_db)],
    x_hub_signature_256: Annotated[str | None, Header()] = None,
) -> Envelope[dict[str, int]]:
    """Upsert a pre-decoded, HMAC-authenticated config batch."""

    secret = get_settings().github_webhook_secret
    body = payload.model_dump_json().encode()
    if (
        secret is None
        or not x_hub_signature_256
        or not verify_signature(body, x_hub_signature_256, secret.get_secret_value())
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid webhook signature")
    count = 0
    for file in payload.files:
        entry = map_config_file(file.path, file.value, payload.commit)
        existing = await db.scalar(
            select(PlatformConfig).where(
                PlatformConfig.config_type == entry.config_type,
                PlatformConfig.config_key == entry.config_key,
            )
        )
        if existing is None:
            existing = PlatformConfig(
                config_type=entry.config_type,
                config_key=entry.config_key,
                config_value=entry.config_value,
                source_path=entry.source_path,
                source_commit=entry.source_commit,
            )
            db.add(existing)
        else:
            existing.config_value = entry.config_value
            existing.source_commit = entry.source_commit
        count += 1
    return Envelope(data={"updated": count})

"""Administrator audit query endpoint."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditEventRecord
from app.db.session import get_db
from app.middleware.session import require
from app.schemas.common import Envelope, Identity

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=Envelope[list[dict[str, Any]]], status_code=status.HTTP_200_OK)
async def list_audit_events(
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[Identity, Depends(require("admin:manage"))],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> Envelope[list[dict[str, Any]]]:
    """Return recent queryable audit events."""

    records = (
        await db.scalars(
            select(AuditEventRecord).order_by(AuditEventRecord.timestamp.desc()).limit(limit)
        )
    ).all()
    return Envelope(
        data=[
            {
                "event_id": str(item.id),
                "event_type": item.event_type,
                "category": item.event_category,
                "actor": item.actor_identity,
                "timestamp": item.timestamp.isoformat(),
                "context": item.additional_context,
            }
            for item in records
        ]
    )

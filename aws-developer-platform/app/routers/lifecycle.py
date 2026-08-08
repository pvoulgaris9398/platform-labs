"""Internal lifecycle scheduler endpoint."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ResourceInventory
from app.db.session import get_db
from app.schemas.common import Envelope
from app.services.lifecycle import due_actions

router = APIRouter(prefix="/lifecycle", tags=["lifecycle"])


@router.post("/run", response_model=Envelope[dict[str, list[str]]], status_code=status.HTTP_200_OK)
async def run_lifecycle(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Envelope[dict[str, list[str]]]:
    """Calculate today's actions; deployment must restrict this route to EventBridge."""

    today = date.today()
    resources = (
        await db.scalars(
            select(ResourceInventory).where(
                ResourceInventory.status.in_(["active", "expiry_pending"])
            )
        )
    ).all()
    actions = {
        str(item.id): sorted(action.value for action in due_actions(item.expiry_date, today))
        for item in resources
    }
    return Envelope(data={key: value for key, value in actions.items() if value})

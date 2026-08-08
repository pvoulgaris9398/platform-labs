"""Approval queue and decisions."""

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ResourceRequest
from app.db.session import get_db
from app.middleware.session import require
from app.schemas.common import Envelope, Identity
from app.schemas.requests import Rejection, RequestStatus, ResourceRequestResponse
from app.utils.state_machine import transition

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get(
    "", response_model=Envelope[list[ResourceRequestResponse]], status_code=status.HTTP_200_OK
)
async def approval_queue(
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[Identity, Depends(require("approvals:manage"))],
) -> Envelope[list[ResourceRequestResponse]]:
    """Return requests awaiting a human decision."""

    records = (
        await db.scalars(
            select(ResourceRequest)
            .where(ResourceRequest.status == RequestStatus.APPROVAL_PENDING.value)
            .order_by(ResourceRequest.created_at)
        )
    ).all()
    return Envelope(data=[ResourceRequestResponse.model_validate(item) for item in records])


@router.post(
    "/{request_id}/approve",
    response_model=Envelope[ResourceRequestResponse],
    status_code=status.HTTP_200_OK,
)
async def approve(
    request_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[Identity, Depends(require("approvals:manage"))],
) -> Envelope[ResourceRequestResponse]:
    """Approve a pending request."""

    record = await db.get(ResourceRequest, request_id)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "request not found")
    record.status = transition(record.status, RequestStatus.APPROVED).value
    record.approved_by = user.principal_arn
    record.approved_at = datetime.now(UTC)
    return Envelope(data=ResourceRequestResponse.model_validate(record))


@router.post(
    "/{request_id}/reject",
    response_model=Envelope[ResourceRequestResponse],
    status_code=status.HTTP_200_OK,
)
async def reject(
    request_id: uuid.UUID,
    payload: Rejection,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[Identity, Depends(require("approvals:manage"))],
) -> Envelope[ResourceRequestResponse]:
    """Reject a pending request with a reason."""

    record = await db.get(ResourceRequest, request_id)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "request not found")
    record.status = transition(record.status, RequestStatus.REJECTED).value
    record.rejected_by = user.principal_arn
    record.rejected_at = datetime.now(UTC)
    record.rejection_reason = payload.reason
    return Envelope(data=ResourceRequestResponse.model_validate(record))

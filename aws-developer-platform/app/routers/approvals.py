"""Approval queue and decisions."""

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ResourceInventory, ResourceRequest
from app.db.session import get_db
from app.middleware.session import require
from app.schemas.common import Envelope, Identity
from app.schemas.requests import Rejection, RequestStatus, ResourceRequestResponse
from app.services.local_provisioner import (
    LocalResourceProvisioner,
    get_local_resource_provisioner,
)
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
    provisioner: Annotated[LocalResourceProvisioner, Depends(get_local_resource_provisioner)],
) -> Envelope[ResourceRequestResponse]:
    """Approve a pending request and provision it in the local POC backend."""

    record = await db.get(ResourceRequest, request_id)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "request not found")
    if record.status == RequestStatus.PROVISIONED.value:
        return Envelope(data=ResourceRequestResponse.model_validate(record))
    if record.status == RequestStatus.FAILED.value:
        raise HTTPException(status.HTTP_409_CONFLICT, "request provisioning already failed")
    if record.status == RequestStatus.APPROVAL_PENDING.value:
        record.status = transition(record.status, RequestStatus.APPROVED).value
        record.approved_by = user.principal_arn
        record.approved_at = datetime.now(UTC)
    elif record.status != RequestStatus.APPROVED.value:
        raise HTTPException(status.HTTP_409_CONFLICT, f"request is not approvable: {record.status}")
    record.status = transition(record.status, RequestStatus.PROVISIONING).value
    try:
        result = await provisioner.provision(record)
    except Exception as exc:
        record.status = transition(record.status, RequestStatus.FAILED).value
        record.provisioning_error = str(exc)
    else:
        record.status = transition(record.status, RequestStatus.PROVISIONED).value
        record.provisioned_arn = result.resource_arn
        record.provisioned_at = datetime.now(UTC)
        db.add(
            ResourceInventory(
                request_id=record.id,
                project_id=record.project_id,
                resource_type=record.resource_type,
                resource_name=record.resource_name,
                resource_arn=result.resource_arn,
                region=record.region,
                environment=record.environment,
                tags=record.tags,
                expiry_date=record.expiry_date,
            )
        )
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

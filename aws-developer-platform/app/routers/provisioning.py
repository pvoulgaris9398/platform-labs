"""Terraform Cloud status callbacks."""

import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import ResourceInventory, ResourceRequest
from app.db.session import get_db
from app.schemas.common import Envelope
from app.schemas.requests import RequestStatus
from app.services.provisioner import verify_signature
from app.utils.state_machine import transition

router = APIRouter(prefix="/provisioning", tags=["provisioning"])
TERMINAL_SUCCESS = {"applied", "planned_and_finished"}
TERMINAL_FAILURE = {"errored", "canceled", "force_canceled", "discarded"}


@router.post(
    "/webhook/tfc", response_model=Envelope[dict[str, str]], status_code=status.HTTP_200_OK
)
async def tfc_webhook(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    x_tfc_signature: Annotated[str | None, Header()] = None,
) -> Envelope[dict[str, str]]:
    """Idempotently apply a terminal Terraform Cloud run status."""

    body = await request.body()
    secret = get_settings().tfc_webhook_secret
    if (
        secret is None
        or not x_tfc_signature
        or not verify_signature(body, x_tfc_signature, secret.get_secret_value())
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid webhook signature")
    payload: dict[str, Any] = await request.json()
    request_id = uuid.UUID(payload["request_id"])
    run_status = str(payload["run_status"])
    record = await db.get(ResourceRequest, request_id)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "request not found")
    if record.status in {RequestStatus.PROVISIONED.value, RequestStatus.FAILED.value}:
        return Envelope(data={"status": record.status})
    if run_status in TERMINAL_SUCCESS:
        record.status = transition(record.status, RequestStatus.PROVISIONED).value
        record.provisioned_arn = payload["resource_arn"]
        record.provisioned_at = datetime.now(UTC)
        db.add(
            ResourceInventory(
                request_id=record.id,
                project_id=record.project_id,
                resource_type=record.resource_type,
                resource_name=record.resource_name,
                resource_arn=record.provisioned_arn,
                region=record.region,
                environment=record.environment,
                tags=record.tags,
                expiry_date=record.expiry_date,
            )
        )
    elif run_status in TERMINAL_FAILURE:
        record.status = transition(record.status, RequestStatus.FAILED).value
        record.provisioning_error = str(payload.get("error", "Terraform run failed"))
    return Envelope(data={"status": record.status})

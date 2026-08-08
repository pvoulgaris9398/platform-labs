"""Resource request submission and retrieval."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Project, ResourceRequest
from app.db.session import get_db
from app.middleware.session import require
from app.schemas.common import Envelope, Identity, Role
from app.schemas.requests import RequestStatus, ResourceRequestCreate, ResourceRequestResponse
from app.services.cost_estimator import check_budget, estimate_monthly_cost
from app.services.guardrail_engine import GuardrailEngine
from app.utils.naming import validate_resource_name
from app.utils.state_machine import transition
from app.utils.tags import missing_required_tags, validate_expiry_date

router = APIRouter(prefix="/requests", tags=["requests"])


@router.get(
    "", response_model=Envelope[list[ResourceRequestResponse]], status_code=status.HTTP_200_OK
)
async def list_requests(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[Identity, Depends(require("requests:read"))],
) -> Envelope[list[ResourceRequestResponse]]:
    """List requests visible to the caller."""

    query = select(ResourceRequest).order_by(ResourceRequest.created_at.desc())
    if user.role is Role.DEVELOPER:
        query = query.where(ResourceRequest.submitted_by == user.principal_arn)
    records = (await db.scalars(query)).all()
    return Envelope(data=[ResourceRequestResponse.model_validate(item) for item in records])


@router.get(
    "/{request_id}",
    response_model=Envelope[ResourceRequestResponse],
    status_code=status.HTTP_200_OK,
)
async def get_request(
    request_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[Identity, Depends(require("requests:read"))],
) -> Envelope[ResourceRequestResponse]:
    """Retrieve one visible request."""

    record = await db.get(ResourceRequest, request_id)
    if record is None or (
        user.role is Role.DEVELOPER and record.submitted_by != user.principal_arn
    ):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "request not found")
    return Envelope(data=ResourceRequestResponse.model_validate(record))


@router.post(
    "", response_model=Envelope[ResourceRequestResponse], status_code=status.HTTP_201_CREATED
)
async def create_request(
    payload: ResourceRequestCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[Identity, Depends(require("requests:create"))],
) -> Envelope[ResourceRequestResponse]:
    """Validate, evaluate, estimate, and persist a resource request."""

    project = await db.get(Project, payload.project_id)
    if project is None or project.status != "active":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "active project not found")
    if payload.resource_type.value not in project.allowed_resource_types:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "resource type not allowed")
    if payload.environment not in project.allowed_environments:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "environment not allowed for project")
    if payload.environment in {"staging", "prod"} and user.role is Role.DEVELOPER:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "team lead required for environment")
    tags = payload.tags | {
        "created_by": user.principal_arn,
        "environment": payload.environment,
        "team": project.team_name,
        "project": project.name,
        "application_name": project.application_name,
        "cost_center": project.cost_center,
        "expiry_date": payload.expiry_date.isoformat(),
    }
    missing = missing_required_tags(tags)
    if missing:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, f"missing tags: {', '.join(sorted(missing))}"
        )
    if not validate_expiry_date(payload.expiry_date):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "expiry date must be within 1-90 days"
        )
    naming = validate_resource_name(
        payload.resource_type,
        project.team_name.casefold(),
        project.name,
        payload.environment,
        payload.name_suffix,
    )
    if not naming.is_valid:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, {"naming_violations": naming.violations}
        )
    warnings = GuardrailEngine().evaluate(payload.resource_type, payload.resource_config)
    estimate = estimate_monthly_cost(payload.resource_type, payload.resource_config)
    budget = check_budget(Decimal(0), estimate, project.monthly_budget_usd)
    request_status = RequestStatus.GUARDRAIL_REVIEW if warnings else RequestStatus.APPROVAL_PENDING
    if budget.requires_exception:
        if not payload.budget_justification:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY, "budget justification required"
            )
        request_status = RequestStatus.BUDGET_REVIEW
    record = ResourceRequest(
        project_id=payload.project_id,
        resource_type=payload.resource_type.value,
        resource_name=naming.value,
        region=payload.region,
        environment=payload.environment,
        resource_config=payload.resource_config,
        tags=tags,
        status=request_status.value,
        guardrail_warnings=[item.model_dump(mode="json") for item in warnings],
        estimated_monthly_cost_usd=estimate,
        cost_estimate_generated_at=datetime.now(UTC),
        budget_justification=payload.budget_justification,
        quota_justification=payload.quota_justification,
        submitted_by=user.principal_arn,
        expiry_date=payload.expiry_date,
    )
    db.add(record)
    await db.flush()
    return Envelope(data=ResourceRequestResponse.model_validate(record))


@router.post(
    "/{request_id}/acknowledge",
    response_model=Envelope[ResourceRequestResponse],
    status_code=status.HTTP_200_OK,
)
async def acknowledge_guardrails(
    request_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[Identity, Depends(require("requests:acknowledge"))],
) -> Envelope[ResourceRequestResponse]:
    """Acknowledge all guardrail warnings and advance to approval."""

    record = await db.get(ResourceRequest, request_id)
    if record is None or record.submitted_by != user.principal_arn:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "request not found")
    record.status = transition(record.status, RequestStatus.APPROVAL_PENDING).value
    record.guardrail_acknowledged_by = user.principal_arn
    record.guardrail_acknowledged_at = datetime.now(UTC)
    record.updated_at = datetime.now(UTC)
    return Envelope(data=ResourceRequestResponse.model_validate(record))

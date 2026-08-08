"""Cost estimate endpoint."""

from decimal import Decimal
from typing import Any

from fastapi import APIRouter, status
from pydantic import BaseModel

from app.schemas.common import Envelope
from app.schemas.requests import ResourceType
from app.services.cost_estimator import estimate_monthly_cost

router = APIRouter(prefix="/cost", tags=["cost"])


class CostEstimateRequest(BaseModel):
    """Cost estimate input."""

    resource_type: ResourceType
    resource_config: dict[str, Any]


@router.post(
    "/estimate", response_model=Envelope[dict[str, Decimal | bool]], status_code=status.HTTP_200_OK
)
async def estimate(payload: CostEstimateRequest) -> Envelope[dict[str, Decimal | bool]]:
    """Return an estimate based on cached fallback pricing."""

    return Envelope(
        data={
            "estimated_monthly_cost_usd": estimate_monthly_cost(
                payload.resource_type, payload.resource_config
            ),
            "stale": True,
        }
    )

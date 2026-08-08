"""Project catalogue and registration."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Project
from app.db.session import get_db
from app.middleware.session import require
from app.schemas.common import Envelope, Identity
from app.schemas.projects import ProjectCreate, ProjectResponse

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=Envelope[list[ProjectResponse]], status_code=status.HTTP_200_OK)
async def list_projects(
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[Identity, Depends(require("projects:read"))],
) -> Envelope[list[ProjectResponse]]:
    """List active projects."""

    records = (await db.scalars(select(Project).order_by(Project.name))).all()
    return Envelope(data=[ProjectResponse.model_validate(item) for item in records])


@router.post("", response_model=Envelope[ProjectResponse], status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[Identity, Depends(require("projects:create"))],
) -> Envelope[ProjectResponse]:
    """Register a project; IAM provisioning is handled asynchronously by its adapter."""

    project = Project(
        **payload.model_dump(),
        default_owner=user.principal_arn,
        registered_by=user.principal_arn,
    )
    db.add(project)
    await db.flush()
    return Envelope(data=ProjectResponse.model_validate(project))

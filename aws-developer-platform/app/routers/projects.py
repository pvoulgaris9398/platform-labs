"""Project catalogue and registration."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Project
from app.db.session import get_db
from app.middleware.session import require
from app.schemas.common import Envelope, Identity, Role
from app.schemas.projects import ProjectCreate, ProjectResponse, ProjectUpdate
from app.services.project_iam import ProjectIamScaffolder, get_project_iam_scaffolder

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=Envelope[list[ProjectResponse]], status_code=status.HTTP_200_OK)
async def list_projects(
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[Identity, Depends(require("projects:read"))],
) -> Envelope[list[ProjectResponse]]:
    """List active projects."""

    query = select(Project).where(Project.status == "active")
    if _user.role is not Role.PLATFORM_ADMIN:
        query = query.where(Project.team_name == _user.team)
    records = (await db.scalars(query.order_by(Project.name))).all()
    return Envelope(data=[ProjectResponse.model_validate(item) for item in records])


@router.post("", response_model=Envelope[ProjectResponse], status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[Identity, Depends(require("projects:create"))],
    iam_scaffolder: Annotated[ProjectIamScaffolder, Depends(get_project_iam_scaffolder)],
) -> Envelope[ProjectResponse]:
    """Register a project and create its initial IAM scaffolding."""

    values = payload.model_dump(exclude={"default_owner"})
    project = Project(
        **values,
        default_owner=payload.default_owner or user.principal_arn,
        registered_by=user.principal_arn,
    )
    db.add(project)
    try:
        await db.flush()
    except IntegrityError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, "project name already exists") from exc
    try:
        roles = await iam_scaffolder.scaffold(project)
    except Exception as exc:
        project.status = "iam_failed"
        project.iam_error_details = str(exc)
    else:
        project.deployer_role_arn = roles.deployer_role_arn
        project.developer_role_arn = roles.developer_role_arn
        project.readonly_role_arn = roles.readonly_role_arn
    return Envelope(data=ProjectResponse.model_validate(project))


async def accessible_project(project_id: uuid.UUID, db: AsyncSession, user: Identity) -> Project:
    """Load a project while enforcing team catalogue boundaries."""

    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "project not found")
    if user.role is not Role.PLATFORM_ADMIN and project.team_name != user.team:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "project not found")
    return project


@router.get("/{project_id}", response_model=Envelope[ProjectResponse])
async def get_project(
    project_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[Identity, Depends(require("projects:read"))],
) -> Envelope[ProjectResponse]:
    """Return project registration and IAM scaffolding details."""

    project = await accessible_project(project_id, db, user)
    return Envelope(data=ProjectResponse.model_validate(project))


@router.patch("/{project_id}", response_model=Envelope[ProjectResponse])
async def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[Identity, Depends(require("projects:update"))],
) -> Envelope[ProjectResponse]:
    """Update the editable portion of a project registration."""

    project = await accessible_project(project_id, db, user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    await db.flush()
    return Envelope(data=ProjectResponse.model_validate(project))


@router.post("/{project_id}/deactivate", response_model=Envelope[ProjectResponse])
async def deactivate_project(
    project_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[Identity, Depends(require("projects:update"))],
) -> Envelope[ProjectResponse]:
    """Remove a project from active catalogues without deleting its resources."""

    project = await accessible_project(project_id, db, user)
    project.status = "deactivated"
    await db.flush()
    return Envelope(data=ProjectResponse.model_validate(project))

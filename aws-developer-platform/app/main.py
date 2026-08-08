"""FastAPI application assembly."""

import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.config import get_settings
from app.db.models import Base
from app.db.session import engine
from app.middleware.rate_limiter import RateLimitMiddleware
from app.middleware.session import SessionMiddleware
from app.routers import (
    admin,
    approvals,
    audit,
    auth,
    cost,
    lifecycle,
    projects,
    provisioning,
    requests,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Create local tables; production uses migrations."""

    if get_settings().environment == "development":
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(title="AWS Developer Platform", version="0.1.0", lifespan=lifespan)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(SessionMiddleware)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=get_settings().allowed_hosts)

for api_router in (
    auth.router,
    requests.router,
    projects.router,
    approvals.router,
    provisioning.router,
    audit.router,
    cost.router,
    admin.router,
    lifecycle.router,
):
    app.include_router(api_router, prefix="/api/v1")


def error_payload(
    code: str, message: str, details: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    """Create the standard error envelope."""

    return {
        "data": None,
        "error": {"code": code, "message": message, "details": details or []},
        "request_id": str(uuid.uuid4()),
    }


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    """Normalize FastAPI HTTP errors."""

    return JSONResponse(
        status_code=exc.status_code, content=error_payload("HTTP_ERROR", str(exc.detail))
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Normalize request validation errors."""

    details = [
        {"field": ".".join(str(part) for part in issue["loc"]), "issue": issue["msg"]}
        for issue in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content=error_payload("VALIDATION_ERROR", "Request validation failed", details),
    )


@app.get("/health", status_code=200)
async def health() -> dict[str, str]:
    """Return process health for the load balancer."""

    return {"status": "ok"}

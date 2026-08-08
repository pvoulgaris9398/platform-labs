"""JWT session middleware and authorization dependencies."""

from collections.abc import Awaitable, Callable

from fastapi import HTTPException, Request, status
from jwt import InvalidTokenError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.config import get_settings
from app.schemas.common import Identity
from app.services.auth import decode_session, is_allowed


class SessionMiddleware(BaseHTTPMiddleware):
    """Populate request state from a valid session cookie when present."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request.state.user = None
        token = request.cookies.get("platform_session")
        if token:
            try:
                request.state.user = decode_session(token, get_settings())
            except InvalidTokenError:
                request.state.user = None
        return await call_next(request)


def current_user(request: Request) -> Identity:
    """Require an authenticated identity."""

    if request.state.user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "authentication required")
    return request.state.user


def require(permission: str) -> Callable[[Request], Identity]:
    """Build a dependency enforcing a named RBAC permission."""

    def dependency(request: Request) -> Identity:
        user = current_user(request)
        if not is_allowed(user.role, permission):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "permission denied")
        return user

    return dependency

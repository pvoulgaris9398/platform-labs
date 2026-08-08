# Python Best Practices

## Language and Runtime
- Target Python 3.13 or 3.14 (current stable as of mid-2026; 3.12 is security-only). Use modern syntax: `match`/`case`, `|` union types in annotations, `tomllib` for config parsing.
- All type hints are mandatory on every function signature (parameters and return type). Use `from __future__ import annotations` in files with forward references.
- Use `X | None` instead of `Optional[X]`. Use `X | Y` instead of `Union[X, Y]`.

## Project Structure
- Follow the module layout defined in `design.md`: `app/routers/`, `app/services/`, `app/middleware/`, `app/schemas/`, `app/utils/`, `app/db/`.
- One class or one logical group of related functions per module. Avoid god modules.
- Keep `app/main.py` thin: app init, middleware registration, router inclusion, lifespan events only. No business logic.

## Dependency Management
- Use `pyproject.toml` with `[project.dependencies]` for runtime deps and `[project.optional-dependencies]` for dev/test deps.
- Pin all dependencies to exact versions (`==`) in `requirements.txt` generated from `pyproject.toml`. No open ranges (`>=`) in production requirements.
- Prefer the standard library over third-party packages where functionality is equivalent.

## FastAPI Conventions
- Define all request/response schemas in `app/schemas/` using Pydantic v2 models. Never use raw `dict` as a parameter type on route handlers.
- Use `Annotated[T, Depends(...)]` dependency injection, not bare `Depends(...)` in function signatures.
- All route handlers must be `async def`. Database calls must use `await` on async sessions.
- Return explicit Pydantic response models on all routes. Set `response_model=` on every router decorator.
- Use `status_code=` explicitly on every route decorator. Do not rely on FastAPI defaults.
- Group related routes under a single `APIRouter` with a `prefix` and `tags`. Include the router in `main.py`.
- Validate path and query parameters using `Annotated` with `Query(...)` / `Path(...)` constraints rather than ad-hoc checks in the handler body.

## Pydantic v2
- Use `model_config = ConfigDict(...)` instead of the deprecated `class Config`. 
- Prefer `model_validator` and `field_validator` over `@validator` (v1 API). Use `mode='before'` or `mode='after'` explicitly.
- Use `model_dump(mode='json')` when serialising for JSON output to ensure datetime/UUID serialisation is correct.
- Do not use mutable defaults — use `default_factory=` for lists and dicts.
- Use `@classmethod` decorator on `model_validator` and `field_validator` methods — required in Pydantic 2.13+.

## SQLAlchemy (Async)
- Use `AsyncSession` with `async with session.begin()` for all transactions. Never commit manually outside a context manager.
- Define all ORM models in `app/db/models.py`. Use `mapped_column()` and `Mapped[T]` (SQLAlchemy 2.x style). Avoid the legacy `Column()` API.
- Never construct raw SQL strings. Use SQLAlchemy Core expressions or ORM queries exclusively (parameterised queries, no injection vectors).
- Always close sessions. Use the `get_db` dependency with `try/finally` or `async with`.

## Error Handling
- Raise `HTTPException` with explicit `status_code` and a `detail` dict matching the standard error envelope: `{"error": {"code": "...", "message": "...", "details": [...]}}`.
- Define custom exception classes in `app/exceptions.py` for domain errors (e.g., `GuardrailViolationError`, `ProvisioningError`). Convert to `HTTPException` in a centralised exception handler registered on the app.
- Never swallow exceptions silently. Log with `logger.exception(...)` (includes traceback) for unexpected errors.
- Use `logger = logging.getLogger(__name__)` at module level. Never use `print()` for application logging.

## Security
- Never hardcode secrets, credentials, or tokens in source code or config files. Always load from AWS Secrets Manager or SSM Parameter Store via `app/config.py`.
- Sanitise all user-supplied strings before using them in AWS API calls, file paths, or log messages.
- Use `secrets.compare_digest()` for any HMAC or token comparison to prevent timing attacks.
- Set `httponly=True`, `samesite="strict"`, `secure=True` on all cookies.

## Testing
- Use `pytest` with `pytest-asyncio` (`asyncio_mode = "auto"` in `pyproject.toml`).
- Use `testcontainers` for integration tests requiring a real PostgreSQL instance.
- Use `unittest.mock.AsyncMock` for mocking async AWS SDK calls.
- Property-based tests use `hypothesis` (6.x, compatible with Python 3.14) with `@settings(max_examples=200)`. Tag each property test with `# Feature: ..., Property N: ...` comment for traceability.
- Aim for ≥80% branch coverage on all `app/services/` and `app/utils/` modules.
- Test files mirror the `app/` directory structure under `tests/`.

## Code Style
- Format with `ruff format` (replaces black). Lint with `ruff check` (0.16.x+) with at minimum the `E`, `F`, `W`, `I`, `UP`, `B`, `S` rule sets enabled.
- Maximum line length: 100 characters.
- Sort imports with `ruff` (isort-compatible). Standard library → third-party → local, each group separated by a blank line.
- Docstrings on all public classes and functions using Google style. Private functions (`_name`) do not require docstrings but must have type hints.

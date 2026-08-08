# General Design Principles

## Architecture
- **Separation of concerns**: routers handle HTTP; services contain business logic; utilities are pure functions with no side effects; models are data containers only. Never put business logic in a router handler or ORM model.
- **Dependency injection over global state**: pass dependencies (db session, config, logger) explicitly via function parameters or FastAPI `Depends()`. Never import a global singleton and call it directly inside a service.
- **Single responsibility**: each module, class, and function should have one reason to change. If a function does two things, split it.
- **Explicit over implicit**: avoid magic. Configuration must be traceable to a source (SSM, env var, config file). Avoid dynamic attribute setting, `__getattr__` magic, and metaprogramming unless there is a compelling reason.

## API Design
- RESTful resource naming: `GET /projects`, `POST /projects`, `GET /projects/{id}`, `PATCH /projects/{id}`, `DELETE /projects/{id}`. Avoid verbs in URLs except for well-established conventions (`/health`, `/auth/session`).
- Use HTTP status codes correctly: 200 (OK), 201 (Created), 204 (No Content), 400 (Bad Request / validation), 401 (Unauthenticated), 403 (Authorised but forbidden), 404 (Not Found), 409 (Conflict), 422 (Unprocessable Entity), 429 (Rate Limited), 500 (Server Error), 503 (Upstream Unavailable).
- All API responses use the standard envelope: `{"data": ..., "error": null}` for success; `{"data": null, "error": {"code": "...", "message": "...", "details": [...]}}` for errors. Never return bare primitives at the top level.
- Version the API from the start: prefix all routes with `/api/v1/`. This avoids costly migrations later.
- Pagination on all list endpoints: use cursor-based pagination (`?cursor=` + `limit=`) for large datasets, offset for admin/audit views. Always include `total`, `next_cursor`, and `items` in paginated responses.

## State Machines
- Represent workflow states as Python `Enum` or TypeScript `const` objects — never raw strings.
- Centralise all valid state transitions in a single transition table. A transition function should check the current state is valid before applying the new state and raise if not.
- Emit an audit event for every state transition as part of the transition function itself — not as an afterthought in the caller.

## Security by Default
- Apply the principle of least privilege everywhere: IAM roles, database users, API permissions. Default to deny.
- Validate and sanitise all external input at the boundary (API layer). Assume inputs are adversarial.
- Never log sensitive data: tokens, passwords, full request bodies containing credentials, or PII beyond what is strictly needed for audit.
- Always use parameterised queries / ORM. Never construct SQL or IAM policy documents from unsanitised user strings.
- HMAC-verify all incoming webhooks before processing.
- Rotate secrets regularly. Secrets must never appear in Git history, logs, or error messages.

## Observability
- Every service should emit structured logs as JSON (key-value pairs, not free-text sentences) so they are queryable in CloudWatch Logs Insights.
- Log at the right level: `DEBUG` for diagnostic detail, `INFO` for normal business events, `WARNING` for recoverable problems, `ERROR` for failures requiring attention. Never use `ERROR` for expected business conditions (e.g., validation failures).
- Include `request_id`, `user_identity`, `project_name`, and `resource_type` as log context fields on every log line within a request scope. Use `contextvars` or a FastAPI middleware to propagate these without threading them through every function signature.
- Every external call (Terraform Cloud, GitHub, AWS APIs) should be wrapped with a log entry at entry and exit showing the operation, duration, and outcome.

## Error Handling
- Fail fast at the boundary: validate inputs fully before doing any work. Do not partially process a request and then fail halfway through.
- Make errors recoverable where possible. Prefer idempotent operations (PUT/PATCH over POST for state changes that must not double-apply).
- Distinguish between retriable and non-retriable errors. Network timeouts and 5xx from external services are retriable. 4xx errors from external services are not.
- When an external service is unavailable, fail gracefully: return a meaningful error to the caller, do not hang waiting for a timeout, and emit an alert.

## Testing Philosophy
- Test behaviour, not implementation. A test should not break if you refactor internals without changing observable behaviour.
- The test pyramid: many unit tests, fewer integration tests, minimal end-to-end tests.
- Property-based tests complement example-based tests — they are not a replacement. Use PBT for functions with well-defined mathematical or logical invariants (validators, calculators, state machines). Use example-based tests for workflow and integration coverage.
- Every bug fixed must have a regression test that reproduces the bug before the fix and passes after.
- Tests must be deterministic and isolated. No test should depend on the order of other tests or on external services (mock them).

## Code Review Standards
- PRs must not exceed 400 lines of changed code. Break large features into stacked PRs.
- Every PR must include: a description of what changed and why, links to relevant requirements/tasks, and confirmation that tests pass.
- No PR is merged with failing tests, lint errors, or type errors.
- Security-sensitive changes (auth, IAM, secrets handling, audit logging) require explicit review by a second person before merge.

# AWS Developer Platform agent guide

## Project purpose

This repository contains the specification for a proof-of-concept internal developer portal. The
portal lets developers request S3 buckets, Lambda functions, and DynamoDB tables through a governed
web UI. It applies naming, tagging, guardrail, budget, quota, approval, lifecycle, and audit controls
before provisioning resources through Terraform Cloud.

The target architecture is a React SPA and a FastAPI service on ECS Fargate, backed by PostgreSQL on
RDS. AWS infrastructure is managed with Terraform. The POC prioritises security, auditability, and
operational simplicity for up to 50 concurrent internal users.

## Authoritative project documents

Read the relevant documents before planning or changing code:

- `.kiro/specs/aws-developer-platform/requirements.md`: product requirements, user stories,
  acceptance criteria, and non-functional requirements.
- `.kiro/specs/aws-developer-platform/design.md`: architecture, interfaces, data model, state
  machines, deployment, security decisions, correctness properties, and test strategy.
- `.kiro/specs/aws-developer-platform/tasks.md`: ordered implementation checklist and traceability
  links. Update its checkboxes when completing an implementation task.
- `.kiro/steering/design-principles.md`: repository-wide architecture, API, security,
  observability, error-handling, testing, and review conventions.
- `.kiro/steering/python.md`: Python, FastAPI, Pydantic, SQLAlchemy, Ruff, and pytest conventions.
- `.kiro/steering/typescript.md`: TypeScript, React, MUI, state-management, accessibility, and
  frontend testing conventions.
- `.kiro/steering/aws-infrastructure.md`: AWS, Terraform, IAM, networking, secrets, observability,
  reliability, and cost conventions.

Do not duplicate or rewrite these documents in generated code or new planning files. Reference the
requirement, design section, correctness property, and task number that a change implements.

If documents conflict, use this precedence: requirements, design, tasks, applicable steering file.
Call out the conflict before implementing a choice that changes an explicit technology version or
architectural decision. Existing dependency manifests and executable tests become authoritative for
the versions actually present once implementation exists; do not perform incidental upgrades.

## Working method

- Use Git Bash as the default interactive shell and write repository commands in portable Bash
  syntax. Prefer POSIX paths, `export NAME=value`, forward slashes, and standard tools such as
  `curl`, `jq`, `sed`, and `rm`. Use PowerShell only when a Windows-specific operation has no
  practical Git Bash equivalent, and label that exception explicitly.
- On Windows, if `pnpm` is not installed globally, invoke the stable pnpm 11 CLI through npm as
  `npx --yes pnpm@latest-11 <command>`. In multi-command Git Bash instructions, define
  `pnpmw() { npx --yes pnpm@latest-11 "$@"; }` and use `pnpmw` consistently.
- Treat the checked state in `tasks.md` and the current repository contents as the record of completed
  work. Do not assume an unchecked task is implemented.
- Work in task order unless the user names a different task or a dependency requires a small,
  documented deviation.
- Keep changes focused on one coherent task. Do not combine unrelated refactors or dependency
  upgrades.
- Preserve traceability. Test property comments must use the design's
  `# Feature: aws-developer-platform, Property N: ...` format.
- When a requirement is ambiguous, consult the design and its correctness properties before asking
  for clarification. Do not invent product behaviour that changes an acceptance criterion.
- Never create, rotate, expose, or commit real credentials. Use documented placeholders and secret
  references only.

## Architecture boundaries

- Routers handle HTTP concerns; services contain business logic; schemas validate boundary data;
  models hold persistence data; utilities are side-effect-free helpers.
- Pass database sessions, configuration, loggers, and external clients explicitly through dependency
  injection. Avoid global mutable state and service singletons.
- Keep `app/main.py` limited to application setup, middleware, routers, exception handlers, and
  lifespan events.
- Centralise request state transitions and emit an audit event from the transition operation itself.
- Wrap Terraform Cloud, GitHub, AWS, and pricing calls behind typed clients or services. Log operation,
  duration, and outcome without logging secrets or sensitive request content.

## API and backend rules

- Prefix routes with `/api/v1/`; use REST resource names and explicit HTTP status codes.
- Return the standard envelope: `{"data": ..., "error": null}` on success and
  `{"data": null, "error": {"code": "...", "message": "...", "details": [...]}}` on failure.
- Use Pydantic v2 request and response models and set `response_model` on every FastAPI route.
- Use async route handlers and SQLAlchemy 2.x `AsyncSession` transaction contexts.
- Validate all external input at the boundary. Use parameterised ORM/Core expressions, constant-time
  secret comparisons, secure cookies, central exception mapping, and structured JSON logging.
- Include `request_id`, `user_identity`, `project_name`, and `resource_type` in request-scoped logs
  when available.

## Frontend rules

- Use function components, strict TypeScript, explicit public API types, and no `any`.
- Use TanStack Query for server state, Zustand only for shared UI state, and local React state for
  component-local concerns. Do not store derived data.
- Route API calls through `src/api/client.ts`; do not call `fetch` directly from components.
- Define forms from Zod schemas and use react-hook-form. Explicitly render loading, error, empty, and
  success states.
- Use MUI theme tokens and accessible semantic controls. Every interaction must work by keyboard,
  have a visible focus state, and expose an accessible name.
- Test behaviour through roles, labels, and accessible names. Use Vitest, Testing Library, user-event,
  and MSW as specified by the design and steering documents.

## AWS and Terraform safety

- Use IAM roles and least-privilege policies. Avoid wildcard resources unless AWS semantics make them
  unavoidable and the exception is documented.
- Put workloads in private subnets. Permit public inbound traffic only to the HTTPS ALB. Use VPC
  endpoints, narrowly scoped security groups, TLS 1.2+, VPC Flow Logs, and explicit log retention.
- Store secrets in Secrets Manager and configuration under the `/platform/` SSM prefix. Inject ECS
  secrets by ARN; never place secret values in Terraform variables, state, source, logs, or plaintext
  environment configuration.
- Define reusable resources under `terraform/modules/` and environment roots under
  `terraform/environments/`. Root modules call modules rather than defining resources directly.
- Pin providers, use remote encrypted state and locking, protect stateful resources from accidental
  destruction, and apply the required project tags to every supported resource.
- Production container references use immutable image digests. Backups, encryption, monitoring,
  public-access blocks, lifecycle policies, budgets, and anomaly detection follow the infrastructure
  steering document.
- Never apply Terraform, change cloud resources, or perform credentialed AWS/Terraform Cloud actions
  unless the user explicitly requests that external change. Plans and validation are safe defaults.

## Verification

Run the narrowest relevant checks first, followed by the broader suite available in the repository.
As applicable, require:

- Python: `ruff format --check`, `ruff check`, type checking configured by the project, and `pytest`.
- Frontend: formatting, ESLint, TypeScript checking, and Vitest.
- Terraform: `terraform fmt -check`, `terraform validate`, `tflint`, and `checkov`.

Every bug fix needs a regression test. Tests must be deterministic and must not depend on live AWS,
Terraform Cloud, GitHub, email, or pricing services. Use mocks for unit tests and documented containers
or fakes for integration tests. Do not claim a task complete or check it off until its implementation
and relevant verification pass.

## Code review rules

- Flag violations of acceptance criteria, correctness properties, state-transition rules,
  least-privilege IAM, audit completeness, secrets handling, and required tagging as substantive
  defects.
- Treat missing validation, missing failure-path tests, nondeterministic tests, unbounded retries, and
  non-idempotent workflow operations as review concerns.
- Security-sensitive changes to authentication, IAM, secrets, audit logging, or network exposure need
  explicit human review.
- Keep proposed pull requests below 400 changed lines where practical and split larger features into
  dependency-ordered changes.

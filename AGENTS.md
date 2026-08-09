# AWS Developer Platform agent guide

## Project purpose

This repository contains the specification for a proof-of-concept internal developer portal. The
portal lets developers request S3 buckets, Lambda functions, and DynamoDB tables through a governed
web UI. It applies naming, tagging, guardrail, budget, quota, approval, lifecycle, and audit controls
before provisioning resources through Terraform Cloud.

The target architecture is a React SPA and a FastAPI service on ECS Fargate, backed by PostgreSQL on
RDS. AWS infrastructure is managed with Terraform. The POC prioritises security, auditability, and
operational simplicity for up to 50 concurrent internal users.

## Codex operating guidance

This file is the Codex-native instruction set for the repository. It contains the project rules,
architecture constraints, implementation order, and coding standards that agents must follow without
requiring a separate project-spec lookup.

When conflicts arise, use this precedence: product requirements, architecture/design decisions,
implementation checklist, language/infrastructure conventions, existing executable tests and
dependency manifests. Call out the conflict before changing an explicit technology version or
architectural decision. Do not perform incidental dependency upgrades.

## Product requirements snapshot

- The platform is a proof-of-concept internal developer portal for governed self-service AWS
  resources through a React SPA and FastAPI API.
- Supported demo resources currently include S3 buckets, Lambda functions, DynamoDB tables, Aurora
  databases, and RDS PostgreSQL instances. The original production target provisions through
  Terraform Cloud; local POC provisioning may target MiniStack when explicitly configured.
- Users authenticate through IAM-role-derived identity. Sessions expose role, team, display name,
  email, and principal ARN.
- Role model: `Developer`, `Team_Lead`, `Platform_Admin`.
- Projects are registered by Team Leads or Platform Admins and seed allowed environments, allowed
  resource types, default owner, budget, tags, and IAM role scaffolding.
- Resource requests must enforce required tags: `cost_center`, `environment`, `team`, `owner`,
  `project`, `application_name`, `expiry_date`, and `created_by`.
- Naming conventions:
  - S3 bucket: `{team}-{project}-{environment}-{name}`, lowercase letters, digits, hyphens, max 63.
  - Lambda function: `{team}-{project}-{environment}-{name}`, lowercase letters, digits, hyphens,
    max 64, must not start with `aws-`.
  - DynamoDB table: `{team}.{project}.{environment}.{name}`, table suffix in PascalCase, max 255.
  - Aurora and RDS PostgreSQL demo names follow the S3-style hyphenated lowercase convention, max 63.
- Developer-accessible environments are `dev` and `uat`; `staging` and `prod` require Team Lead
  authority.
- Requests move through guarded workflow states: pending, guardrail review, approval pending,
  approved, provisioning, provisioned, failed, rejected, expired, and lifecycle states.
- Guardrails are soft warnings requiring acknowledgement or Team Lead approval flow; never silently
  bypass guardrail warnings.
- Project budget and quota checks are soft governance gates with justification and Team Lead review.
- Every state transition and security-sensitive action must be auditable.
- Local MiniStack is acceptable for the POC, but it is not an IAM/security-enforcement substitute for
  real AWS. Keep local adapters isolated so production AWS/Terraform integration can replace them.

## Architecture and implementation order

- React SPA uses MUI, TanStack Query, React Router, react-hook-form, and Zod.
- FastAPI service owns API routes, validation, state transitions, local provisioning adapters, and
  persistence.
- PostgreSQL is the application database target; local development may use SQLite if already wired.
- Terraform Cloud is the production provisioning target, wrapped behind typed clients/services.
- Mutable platform configuration is represented as code/data, with database caching where needed.
- Work in dependency order unless the user explicitly names a different task or a small dependency
  deviation is required.
- Treat the implementation checklist and current repository contents as the completion record. Do
  not mark a task complete until implementation and relevant verification pass.

## Extracted design principles

- Routers handle HTTP concerns only. Services contain business logic. Utilities are side-effect-free.
  ORM models are persistence containers, not business-logic hosts.
- Pass database sessions, settings, loggers, and external clients through dependency injection. Avoid
  global mutable state and untyped service singletons.
- Keep `app/main.py` limited to app assembly, middleware, router inclusion, exception handlers, and
  lifespan events.
- Prefer explicit configuration over magic. Runtime configuration must be traceable to env, SSM,
  Secrets Manager, or documented local defaults.
- Centralise state transitions in a transition table/function. Do not scatter status string updates.
- Wrap AWS, Terraform Cloud, GitHub, pricing, and MiniStack calls behind typed service adapters.
- External calls should log operation, duration, and outcome without secrets.
- Keep PR-sized changes focused; avoid unrelated refactors and dependency upgrades.

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
- Model finite TypeScript domain values as explicit unions of named literal aliases, backed by
  runtime constants for validation and UI options. For example:
  `type ResourceType = S3ResourceType | LambdaResourceType`, where each member is
  `typeof ResourceTypes.S3`, `typeof ResourceTypes.Lambda`, and so on. Do not use a loose `string`,
  a hand-written anonymous string union, or a tuple-index shortcut as the canonical domain model.
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

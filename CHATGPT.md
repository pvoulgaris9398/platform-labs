# ChatGPT project instructions

Use these instructions when ChatGPT is helping with this repository outside the Codex agent runtime.
Codex-specific workflow rules live in `AGENTS.md`; this file is the ChatGPT-facing equivalent.

## Project context

This repository implements a proof-of-concept AWS Developer Platform: an internal self-service portal
where developers request governed cloud resources through a React SPA backed by a FastAPI API.

The portal enforces authentication, project onboarding, naming, required tags, soft guardrails,
budget/quota gates, approval workflow, lifecycle tracking, auditability, and local/demo provisioning.

Supported demo resources currently include:

- S3 buckets
- Lambda functions
- DynamoDB tables
- Amazon Aurora databases
- Amazon RDS for PostgreSQL instances

Local POC provisioning may use MiniStack. Production-oriented provisioning must remain isolated behind
typed adapters so Terraform Cloud or real AWS can replace the local backend later.

## Product rules

- Role model: `Developer`, `Team_Lead`, `Platform_Admin`.
- Team Leads and Platform Admins can register projects. Projects define allowed environments, allowed
  resource types, default owner, cost center, monthly budget, and local IAM scaffolding status.
- Developers can request resources only in project-allowed environments and resource types.
- `dev` and `uat` are developer-accessible. `staging` and `prod` require Team Lead authority.
- Required request tags: `cost_center`, `environment`, `team`, `owner`, `project`,
  `application_name`, `expiry_date`, `created_by`.
- Naming:
  - S3: `{team}-{project}-{environment}-{name}`, lowercase letters/digits/hyphens, max 63.
  - Lambda: `{team}-{project}-{environment}-{name}`, lowercase letters/digits/hyphens, max 64, not
    `aws-*`.
  - DynamoDB: `{team}.{project}.{environment}.{name}`, suffix in PascalCase, max 255.
  - Aurora and RDS PostgreSQL demo names use lowercase hyphenated AWS-friendly identifiers, max 63.
- Requests move through a controlled state machine. Do not update statuses ad hoc.
- Soft guardrails create review/acknowledgement work; do not silently skip them.
- Budget/quota exceptions require justification and review.
- Security-sensitive actions and state transitions must be auditable.

## Architecture rules

- Routers handle HTTP. Services contain business logic. Utilities are pure where practical. ORM models
  describe persistence only.
- Use dependency injection for sessions, settings, loggers, and external clients.
- Keep `app/main.py` thin.
- Wrap MiniStack, AWS, Terraform Cloud, GitHub, pricing, and notification calls behind typed service
  adapters.
- Keep local POC behavior explicit and replaceable. Do not mix real credentialed AWS operations into
  local demo code.

## Backend rules

- FastAPI routes are under `/api/v1`.
- All responses use the standard envelope: `{"data": ..., "error": null}` or
  `{"data": null, "error": {"code": "...", "message": "...", "details": [...]}}`.
- Use Pydantic v2 schemas for request/response boundaries.
- Use SQLAlchemy async sessions and parameterized ORM/Core expressions.
- Never log secrets, credentials, full sensitive request bodies, or plaintext token material.
- Use Ruff formatting/checking and pytest.

## Frontend rules

- Use React function components, strict TypeScript, MUI, TanStack Query, React Router,
  react-hook-form, and Zod.
- Route API calls through `src/api/client.ts`.
- Explicitly render loading, error, empty, and success states.
- Model finite domain values as explicit unions of named literal aliases, backed by runtime constants
  for validation and UI options. For example:

```ts
export const ResourceTypes = { S3: 's3', Lambda: 'lambda' } as const;
export type S3ResourceType = typeof ResourceTypes.S3;
export type LambdaResourceType = typeof ResourceTypes.Lambda;
export type ResourceType = S3ResourceType | LambdaResourceType;
```

- Derive UI option lists and metadata from those constants. Do not maintain duplicated string unions
  and UI option lists. Do not use a loose `string`, a hand-written anonymous string union, or a
  tuple-index shortcut as the canonical domain model.
- Keep service-specific presentation logic out of page components. Put mapping and URL generation in
  typed helpers with exhaustive `switch` statements.
- Test UI behavior through roles, labels, and accessible names.

## Verification expectations

- Backend changes: run Ruff and pytest.
- Frontend changes: run TypeScript build and Vitest. ESLint may require project config before it can
  run in this repo.
- Every bug fix gets a regression test.
- Do not claim a feature complete unless implementation and relevant verification pass.

## Safety

- Never create, rotate, expose, or commit real credentials.
- Never apply Terraform, change cloud resources, or perform credentialed AWS/Terraform Cloud actions
  unless explicitly asked.
- MiniStack is acceptable for local demos but does not fully model AWS IAM/security behavior.

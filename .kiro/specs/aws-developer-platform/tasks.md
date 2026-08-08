# Implementation Plan: AWS Developer Platform

## Overview

Implement the AWS Developer Platform — a self-service internal developer portal backed by a FastAPI (Python 3.12) API on ECS Fargate, a React + MUI v5 SPA, PostgreSQL 15 on RDS, Terraform Cloud for provisioning, dual-write audit logging to CloudWatch Logs and S3 with Object Lock, EventBridge Scheduler for lifecycle management, and SNS for notifications. The implementation is organised into the following epics:

1. Project scaffolding and database foundation
2. Authentication and session management
3. Naming convention validators and shared utilities
4. Resource request API (submission, validation, guardrail evaluation)
5. Approval workflow and state machine
6. Terraform Cloud provisioner integration
7. IAM policy builder and project onboarding
8. Audit logger (dual-write)
9. Lifecycle scheduler and expiry enforcement
10. Cost estimation and budget/quota checks
11. Platform administration (config sync, dropdowns, guardrails)
12. Security middleware (rate limiting, session, security headers)
13. React SPA — core shell, routing, and auth flow
14. React SPA — resource request wizard
15. React SPA — approval queue, project catalogue, admin pages
16. Property-based test suite
17. Integration test suite

---

## Tasks

- [ ] 1. Project scaffolding and database foundation
  - [ ] 1.1 Initialise the FastAPI project structure
    - Create the directory tree under `app/` as defined in the design: `routers/`, `services/`, `middleware/`, `schemas/`, `utils/`, `db/`
    - Create `app/main.py` with FastAPI app init, CORS config (internal origins only), and a `GET /health` endpoint returning `{"status": "ok"}`
    - Create `app/config.py` using `pydantic-settings`; load all config from SSM Parameter Store paths defined in the design (db host, db name, TFC org, GitHub repo, session timeouts)
    - Add `pyproject.toml` (or `requirements.txt`) pinning: fastapi, uvicorn, sqlalchemy[asyncio], asyncpg, pydantic[v2], boto3, httpx, python-jose[cryptography], hypothesis
    - _Requirements: NFR-7.3_

  - [ ] 1.2 Implement PostgreSQL schema via SQLAlchemy ORM models
    - Create `app/db/session.py` — async SQLAlchemy engine and `AsyncSession` factory using connection URL from `config.py`; configure connection pool (pool_size=5, max_overflow=10)
    - Create `app/db/models.py` with ORM models matching all five tables: `projects`, `requests`, `audit_events`, `platform_config`, `resource_inventory` — use all column definitions, indexes, and constraints from the design's PostgreSQL schema
    - Create `alembic.ini` and `alembic/env.py`; generate the initial migration that creates all five tables with their indexes
    - _Requirements: Requirement 2.5, Requirement 9, NFR-7.5_

  - [ ] 1.3 Implement Pydantic v2 request/response schemas
    - Create `app/schemas/requests.py` — `ResourceRequestCreate`, `ResourceRequestResponse`, `ResourceRequestStatus` schemas covering all fields from the `requests` table; use discriminated unions for `resource_config` per resource type (S3Config, LambdaConfig, DynamoDBConfig)
    - Create `app/schemas/projects.py` — `ProjectCreate`, `ProjectResponse`, `ProjectUpdate` schemas
    - Create `app/schemas/audit.py` — `AuditEvent` Pydantic model matching the structured JSON schema from the design; include all required fields with strict types
    - _Requirements: Requirement 2, Requirement 14, Requirement 9_


- [ ] 2. Authentication and session management
  - [ ] 2.1 Implement the STS authentication router
    - Create `app/routers/auth.py` with `POST /auth/session` accepting `{access_key, secret_key, session_token}`
    - Call `sts:GetCallerIdentity` server-side using the supplied credentials; extract role ARN and session name from the returned ARN
    - Call `iam:GetRole` + `iam:ListRoleTags` to fetch the `platform:role`, `email`, `team`, and `display_name` tags from the assumed role
    - Validate the role ARN against the authorised role list in `platform_config`; return 401 with a descriptive message if not authorised
    - Map `platform:role` tag to portal role enum: `Developer` | `Team_Lead` | `Platform_Admin` (default `Developer`)
    - Generate a signed JWT (HS256, signed with `platform/session/jwt_secret` from Secrets Manager) containing claims: `sub`, `session_name`, `role`, `team`, `email`, `iat`, `exp` (max 8 hours)
    - Set the JWT as an `HttpOnly`, `SameSite=Strict` cookie named `platform_session`; return `{role, team, display_name, session_expires_at}` in the JSON body
    - _Requirements: Requirement 1.1, 1.2, 1.3, 1.4, 1.5_

  - [ ] 2.2 Implement session middleware and JWT validation
    - Create `app/middleware/session.py` — FastAPI middleware that extracts the `platform_session` cookie, validates the JWT signature and expiry, and injects `request.state.user` (identity, role, team, email, session_issued_at, last_activity_at)
    - Return 401 if the cookie is absent, the JWT is invalid, or the token is expired
    - On each valid request, update `last_activity_at` in the session context (in-memory per-request; not persisted to DB for performance)
    - Add `DELETE /auth/session` endpoint to clear the cookie (logout)
    - _Requirements: Requirement 1.2, NFR-8.1, NFR-8.2, NFR-8.5_

  - [ ]* 2.3 Write property test for session expiry logic
    - **Property 13: Session expiry logic is correct**
    - **Validates: Requirements NFR-8.1, NFR-8.2, NFR-8.3**
    - Generate arbitrary `(session_issued_at, last_activity_at, current_time)` triples with `session_issued_at ≤ last_activity_at ≤ current_time`
    - Assert expired when idle timeout exceeded; assert expired when absolute limit exceeded; assert warn when within warning threshold
    - _Tag: `# Feature: aws-developer-platform, Property 13: Session expiry logic is correct`_

  - [ ]* 2.4 Write unit tests for auth router
    - Test happy path: valid credentials → JWT cookie set, correct role extracted
    - Test 401 path: role ARN not in authorised list
    - Test 401 path: invalid/expired credentials (mock STS returning error)
    - _Requirements: Requirement 1.1, 1.4_


- [ ] 3. Naming convention validators and shared utilities
  - [ ] 3.1 Implement naming convention validators in `app/utils/naming.py`
    - Implement `validate_s3_name(team, project, environment, name_suffix) -> ValidationResult` — construct full name `{team}-{project}-{environment}-{name_suffix}`; enforce: lowercase alphanumeric + hyphens only, max 63 chars, no leading/trailing hyphen; return `ValidationResult(is_valid, violations)` listing each violated rule
    - Implement `validate_lambda_name(team, project, environment, name_suffix) -> ValidationResult` — same construction; enforce: lowercase alphanumeric + hyphens, max 64 chars, must not start with `aws-`; return violations per rule
    - Implement `validate_dynamodb_name(team, project, environment, name_suffix) -> ValidationResult` — construct `{team}.{project}.{environment}.{name_suffix}`; enforce: alphanumeric + hyphens + underscores + dots, max 255 chars, `name_suffix` must be PascalCase; return violations per rule
    - _Requirements: Requirement 3.1–3.19_

  - [ ]* 3.2 Write property test for resource naming validation
    - **Property 5: Resource naming validation is consistent**
    - **Validates: Requirements 3.1–3.19**
    - Use Hypothesis `@given` with generated `team`, `project`, `environment`, and `name_suffix` strings
    - For each validator: assert `is_valid == True` iff all constraints satisfied; assert violations list is non-empty when `is_valid == False`; assert no exceptions raised for any string input
    - _Tag: `# Feature: aws-developer-platform, Property 5: Resource naming validation is consistent`_

  - [ ] 3.3 Implement required tag validators in `app/utils/tags.py`
    - Implement `validate_required_tags(tags: dict, resource_type: str) -> ValidationResult` — check presence and non-emptiness of all seven required tags: `cost_center`, `environment`, `team`, `owner`, `project`, `application_name`, `expiry_date`
    - Implement `validate_expiry_date(submission_date: date, expiry_date: date) -> ValidationResult` — enforce: `submission_date < expiry_date ≤ submission_date + 90 days`; return violation message distinguishing past-date vs. exceeds-90-day cases
    - Implement `validate_cost_center(value: str, allowed_values: list[str]) -> ValidationResult`
    - _Requirements: Requirement 4.1–4.18_

  - [ ]* 3.4 Write property test for expiry date validation
    - **Property 6: Expiry date validation enforces the future-date and 90-day ceiling**
    - **Validates: Requirements 4.14, 4.15, 4.16**
    - Use Hypothesis date strategies to generate `(submission_date, proposed_expiry_date)` pairs across a wide date range
    - Assert accept iff `submission_date < proposed_expiry_date ≤ submission_date + 90 days`; assert correct violation message returned in each rejection case
    - _Tag: `# Feature: aws-developer-platform, Property 6: Expiry date validation enforces the future-date and 90-day ceiling`_


- [ ] 4. Resource request API
  - [ ] 4.1 Implement the requests router — create and retrieve
    - Create `app/routers/requests.py`
    - `POST /requests` — validate JWT (Developer or Team_Lead); run field presence validation via `validate_required_tags`; run naming convention validation for the selected resource type; validate expiry date; validate `cost_center` against `platform_config`; auto-populate `created_by` tag from JWT claims; persist request with `status='pending'`; return `ResourceRequestResponse` with assigned UUID
    - `GET /requests` — return paginated list of requests belonging to `request.state.user` (Developers see own requests; Platform_Admin sees all; filter by `status`, `project_id`, date range)
    - `GET /requests/{id}` — return full request detail including `guardrail_warnings`, `rejection_reason`, `provisioned_arn`, all tags
    - Enforce environment access control: reject with 403 if Developer attempts `staging` or `prod`
    - _Requirements: Requirement 2.1–2.6, Requirement 4, Requirement 8, Requirement 14.5–14.7_

  - [ ]* 4.2 Write property test for request validation completeness
    - **Property 3: Request validation rejects incomplete submissions**
    - **Validates: Requirements 2.3, 2.6, 4.18**
    - Use Hypothesis to generate request objects with arbitrary subsets of required fields missing or whitespace-only
    - Assert the validation function returns a rejection containing exactly the names of all and only the missing/empty fields
    - _Tag: `# Feature: aws-developer-platform, Property 3: Request validation rejects incomplete submissions`_

  - [ ]* 4.3 Write property test for request ID uniqueness
    - **Property 4: Request IDs are universally unique**
    - **Validates: Requirement 2.5**
    - Generate N request creation calls (N in 2..100 via Hypothesis); assert all returned IDs are distinct UUIDs
    - _Tag: `# Feature: aws-developer-platform, Property 4: Request IDs are universally unique`_

  - [ ]* 4.4 Write unit tests for requests router
    - Test 422 for missing required field (one test per required field)
    - Test 403 for Developer selecting `staging` environment
    - Test 422 for naming convention violation (one case per resource type)
    - Test 422 for `cost_center` not in allowed list
    - _Requirements: Requirement 2, Requirement 3, Requirement 4, Requirement 14.6_


- [ ] 5. Guardrail engine
  - [ ] 5.1 Implement the guardrail engine core and base rule class
    - Create `app/services/guardrail_engine/base.py` — abstract `GuardrailRule` with fields `rule_id`, `name`, `description`, `resource_type`, `enabled`; abstract method `evaluate(request: ResourceRequest) -> Optional[GuardrailWarning]`
    - Create `app/services/guardrail_engine/__init__.py` — `GuardrailEngine` class with `load_rules(resource_type, config_cache)` and `evaluate(request) -> List[GuardrailWarning]`; load_rules reads enabled state and thresholds from `platform_config` cache; evaluate iterates all enabled rules and collects non-None warnings
    - _Requirements: Requirement 5.1, 5.2_

  - [ ] 5.2 Implement S3 guardrail rules (S3-G1 through S3-G5)
    - Create `app/services/guardrail_engine/s3_rules.py`
    - S3-G1: warn if `block_public_access` not explicitly enabled
    - S3-G2: warn if `versioning_enabled` is false or absent
    - S3-G3: warn if `encryption` is not set to `SSE-S3` or `SSE-KMS`
    - S3-G4: warn if no `lifecycle_policy` specified; include recommendation for 90-day IA/Glacier transition for dev/uat
    - S3-G5: warn if `logging_enabled` is false or absent
    - _Requirements: Requirement 5.7_

  - [ ] 5.3 Implement Lambda guardrail rules (L-G1 through L-G7)
    - Create `app/services/guardrail_engine/lambda_rules.py`
    - L-G1: warn if `memory_mb > 512` for dev/uat
    - L-G2: warn if `timeout_seconds > 30` for dev/uat
    - L-G3: warn if `reserved_concurrency` not set; include recommendation of ≤10 for dev/uat
    - L-G4: warn if `runtime` is in the deprecated list (python3.8, nodejs14.x, etc.)
    - L-G5: warn if `vpc_enabled` is false
    - L-G6: warn if `xray_tracing_enabled` is false
    - L-G7: warn if any plaintext env var name contains `SECRET`, `PASSWORD`, `TOKEN`, or `KEY` (case-insensitive match on variable name); exempt variables marked as `secret_reference`
    - _Requirements: Requirement 5.8, NFR-10.5_

  - [ ] 5.4 Implement DynamoDB guardrail rules (D-G1 through D-G6)
    - Create `app/services/guardrail_engine/dynamodb_rules.py`
    - D-G1: warn if `billing_mode = PROVISIONED` for dev/uat; recommend `PAY_PER_REQUEST`
    - D-G2: warn if provisioned capacity and `rcu > 25` or `wcu > 25` for dev/uat
    - D-G3: warn if `pitr_enabled` is false
    - D-G4: warn if `encryption_enabled` is false
    - D-G5: warn if `ttl_attribute` is absent for dev/uat
    - D-G6: warn if `table_class` is not considered `STANDARD_INFREQUENT_ACCESS` for infrequently accessed data (treat as always-warn when `table_class` is absent)
    - _Requirements: Requirement 5.9_

  - [ ]* 5.5 Write property test for guardrail evaluation soundness and completeness
    - **Property 7: Guardrail evaluation is complete and sound**
    - **Validates: Requirements 5.1, 5.2, 5.7, 5.8, 5.9**
    - Use Hypothesis to generate arbitrary S3, Lambda, and DynamoDB request configs; enable all rules
    - Assert soundness: every warning in result corresponds to a violated rule condition
    - Assert completeness: every rule whose condition is violated appears in the result
    - Assert disabled rules never appear in results regardless of config
    - _Tag: `# Feature: aws-developer-platform, Property 7: Guardrail evaluation is complete and sound`_

  - [ ] 5.6 Wire guardrail evaluation into the request submission flow
    - In `app/routers/requests.py` `POST /requests`: after field validation passes, call `GuardrailEngine.evaluate(request)`; if warnings returned, set status to `guardrail_review` and attach warnings to the request record; if no warnings, set status to `approval_pending`
    - Add `POST /requests/{id}/acknowledge-warnings` endpoint — Developer acknowledges all warnings (records `guardrail_acknowledged_at`, `guardrail_acknowledged_by`); transitions status from `guardrail_review` to `approval_pending`
    - _Requirements: Requirement 5.3, 5.4, 5.5, 5.6_

  - [ ] 5. Checkpoint — Ensure all tests pass, ask the user if questions arise.


- [ ] 6. Approval workflow and request state machine
  - [ ] 6.1 Implement the approvals router
    - Create `app/routers/approvals.py`
    - `GET /approvals` — return all requests in `approval_pending`, `budget_review`, or `quota_review` status belonging to the authenticated Team_Lead's team; Platform_Admin sees all pending approvals
    - `POST /approvals/{request_id}/approve` — transition status from `approval_pending` to `approved`; record `approved_by`, `approved_at`; trigger provisioner (call `provisioner.py` async task)
    - `POST /approvals/{request_id}/reject` — transition to `rejected`; require non-empty `rejection_reason` in body; record `rejected_by`, `rejected_at`, `rejection_reason`
    - `POST /approvals/{request_id}/budget-exception` — Team_Lead approve/deny budget exception; on approve, transition `budget_review` → `approval_pending`; on deny, transition → `rejected`
    - `POST /approvals/{request_id}/quota-exception` — same pattern as budget exception for quota_review
    - _Requirements: Requirement 6.1–6.5_

  - [ ] 6.2 Implement request expiry via EventBridge-triggered scheduled check
    - Add a `GET /internal/lifecycle/expire-pending` endpoint (protected by internal API key from SSM, not JWT) that queries for requests in `approval_pending` status where `created_at < now() - 7 days`
    - For each matching request: transition status to `expired`; emit SNS notification to the submitting developer's email (extracted from request record)
    - Wire this endpoint as a secondary lifecycle target (the primary lifecycle endpoint handles resource expiry; this handles request expiry)
    - _Requirements: Requirement 6.6, 6.7_

  - [ ]* 6.3 Write unit tests for approval workflow
    - Test approve: status transitions correctly, provisioner is called
    - Test reject: rejection reason stored, 422 if reason is empty
    - Test budget exception approve/deny flow
    - Test quota exception approve/deny flow
    - Test expiry: requests older than 7 days transition to `expired`
    - _Requirements: Requirement 6.1–6.7_


- [ ] 7. Terraform Cloud provisioner service
  - [ ] 7.1 Implement the Terraform Cloud API client
    - Create `app/services/provisioner.py` with `ProvisionerService` class
    - Implement `trigger_run(workspace_id: str, variables: dict) -> str` — call `POST /api/v2/runs` on the TFC API; pass resource config and tags as run variables; return `run_id`
    - Implement `get_run_status(run_id: str) -> RunStatus` — call `GET /api/v2/runs/{run_id}`; return status enum (pending, planning, applying, applied, errored, cancelled)
    - Implement `get_workspace_id(resource_type: str, project_name: str) -> str` — look up or create workspace named `platform-{resource_type}-{project_name}`
    - TFC API token fetched from Secrets Manager at service init; use `httpx.AsyncClient` for all calls
    - _Requirements: Requirement 7.1, 7.2_

  - [ ] 7.2 Implement TFC webhook receiver and polling fallback
    - Create `app/routers/provisioning.py` with `POST /provisioning/webhook/tfc`
    - Verify HMAC-SHA256 signature from `X-TFE-Notification-Signature` header against webhook secret stored in SSM
    - Extract `run_id`, `status`, and `outputs` (including `resource_arn`) from webhook payload
    - If `status == applied`: transition request to `provisioned`, store `provisioned_arn`, insert row into `resource_inventory`, trigger IAM policy update (see task 8.2)
    - If `status == errored|cancelled`: transition to `failed`, store `provisioning_error`
    - Implement polling fallback as a FastAPI background task: for any request in `provisioning` status with `updated_at < now() - 5 minutes`, poll TFC every 60 seconds; after 30 minutes, transition to `provisioning_warning` and publish to SNS `platform-provisioning-alerts`
    - Make webhook handler idempotent: check current DB status before applying any transition
    - _Requirements: Requirement 7.3, 7.4, 7.5, NFR-7.4_

  - [ ]* 7.3 Write unit tests for provisioner service
    - Test `trigger_run`: mock httpx, assert correct TFC API payload structure per resource type (S3, Lambda, DynamoDB)
    - Test webhook handler: idempotency (same webhook twice → single transition), HMAC rejection on invalid signature
    - Test polling fallback: mock TFC status returning `applied` after 2 polls
    - Test stuck run: after 30 minutes, verify `provisioning_warning` status and SNS publish
    - _Requirements: Requirement 7.1–7.5_


- [ ] 8. IAM policy builder and project onboarding
  - [ ] 8.1 Implement the IAM policy document builder
    - Create `app/services/iam_policy.py` with `IamPolicyBuilder` class
    - Implement `build_deployer_policy(s3_arns, lambda_arns, dynamodb_arns) -> dict` — generate AWS IAM policy JSON with statements covering exactly the S3, Lambda, and DynamoDB permission sets defined in Requirement 11.2; scope each statement's `Resource` to only the provided ARNs; include `Version: "2012-10-17"` and `Effect: Allow`
    - Implement `build_developer_policy(s3_arns, lambda_arns, dynamodb_arns) -> dict` — generate policy with the developer read-only permissions from Requirement 14.8b
    - Implement `build_readonly_policy(s3_arns, lambda_arns, dynamodb_arns) -> dict` — generate policy with the consumer-level permissions from Requirement 14.8c
    - Implement `add_ssm_secrets_permissions(policy: dict, project_path_prefix: str) -> dict` — add `ssm:GetParameter` and `secretsmanager:GetSecretValue` scoped to the project's path prefix (per NFR-10.6)
    - Return empty `{"Version":"2012-10-17","Statement":[]}` policy when all ARN lists are empty (initial project registration placeholder)
    - _Requirements: Requirement 11.1–11.4, Requirement 14.8, NFR-10.6_

  - [ ]* 8.2 Write property test for IAM policy least-privilege invariant
    - **Property 9: IAM policy least-privilege invariant**
    - **Validates: Requirements 11.1–11.4, 14.8**
    - Use Hypothesis to generate arbitrary sets of `{s3_arns, lambda_arns, dynamodb_arns}`
    - For each generated set: assert every ARN in the input is covered in the policy; assert no ARN outside the input appears; assert all actions are drawn exclusively from the permitted list per role type; assert policy JSON is valid (parseable, `Version` present, all `Effect` values are `Allow` or `Deny`)
    - _Tag: `# Feature: aws-developer-platform, Property 9: IAM policy least-privilege invariant`_

  - [ ] 8.3 Implement the projects router and IAM scaffolding trigger
    - Create `app/routers/projects.py`
    - `POST /projects` — validate project name (alphanumeric + hyphens, max 32 chars, unique); persist project record with `status='active'`; trigger TFC run on `platform-iam-{project_name}` workspace to create the three IAM roles (deployer, developer, readonly) with placeholder policies; on TFC run success update project with all three role ARNs and set status to `active`; on failure set `status='iam_failed'` and store error
    - `GET /projects` — return active projects accessible to the requesting user's team
    - `GET /projects/{id}` — return project detail including IAM role ARNs
    - `PATCH /projects/{id}` — allow Team_Lead to update description, allowed_environments, allowed_resource_types, default_owner
    - `POST /projects/{id}/deactivate` — set status to `deactivated`; remove from developer dropdown lists
    - _Requirements: Requirement 14.1–14.14_

  - [ ] 8.4 Implement incremental IAM policy update after resource provisioning
    - In `app/services/provisioner.py`, after a successful provisioning run: fetch all provisioned ARNs for the project from `resource_inventory`; call `IamPolicyBuilder` to generate updated policies for all three roles; trigger a TFC run on `platform-iam-{project_name}` workspace; on completion emit `iam.policy_updated` audit event; update project record with latest role ARNs
    - If the resource is in `expiry_pending` status, skip adding it to the deployer policy update (per NFR-12.3b)
    - After a successful deprovisioning run: remove the deprovisioned ARN from all three role policies via the same IAM workspace run; emit `iam.policy_updated` audit event
    - _Requirements: Requirement 11.4, Requirement 11.5, NFR-12.3b, NFR-12.7b_

  - [ ] 8. Checkpoint — Ensure all tests pass, ask the user if questions arise.


- [ ] 9. Audit logger (dual-write)
  - [ ] 9.1 Implement the AuditLogger service
    - Create `app/services/audit_logger.py` with `AuditLogger` class and `emit(event: AuditEvent) -> None` async method
    - Implement `_write_cloudwatch(json_payload: str)` — use `boto3` `put_log_events` to write to log group `/platform/audit`, log stream `YYYY-MM-DD` (create stream if it does not exist); batch up to 10,000 events
    - Implement `_write_s3(json_payload: str)` — use `boto3` `put_object` to write to `platform-audit-{account_id}` bucket with key `audit/{year}/{month}/{day}/{event_id}.json`; each event is a separate object
    - Use `asyncio.gather` with `return_exceptions=True` to fire both writes concurrently; if either raises, log to fallback local logger and raise `AuditWriteError` (non-blocking — caller must handle in background task)
    - Mirror each audit event to the `audit_events` PostgreSQL table for in-portal queryability
    - _Requirements: Requirement 9.1–9.11, NFR-2.1–2.5_

  - [ ] 9.2 Implement audit middleware for automatic event emission
    - Create `app/middleware/audit_middleware.py` — after response is sent (using FastAPI `BackgroundTasks`), emit an `AuditEvent` for every POST/PATCH/DELETE request; extract `event_type` from the route path and HTTP method; populate `actor_identity` from `request.state.user`, `source_ip` from request headers, `timestamp` from UTC now
    - Add `app/routers/audit.py` with `GET /audit/events` (Platform_Admin only) — paginated, filterable by `event_category`, `actor_identity`, `project_name`, date range
    - _Requirements: Requirement 9.2, 9.3, 9.4, NFR-2.4_

  - [ ]* 9.3 Write property test for audit event completeness
    - **Property 8: Audit events are emitted for every state transition**
    - **Validates: Requirements 9.1, 9.2, NFR-2.4**
    - For each defined state transition (14 transitions from the state machine), verify that calling the transition function exactly once causes exactly one `AuditEvent` to be emitted containing the correct `event_type`, `request_id`, `actor_identity`, and a valid UTC `timestamp`
    - Use Hypothesis to generate arbitrary valid `request_id` and `actor_identity` values
    - _Tag: `# Feature: aws-developer-platform, Property 8: Audit events are emitted for every state transition`_

  - [ ]* 9.4 Write unit tests for audit logger
    - Test dual-write: both CloudWatch and S3 writes invoked with identical payloads
    - Test partial failure: if S3 write fails, `AuditWriteError` raised, fallback logger called
    - Test S3 object key format: assert `audit/{year}/{month}/{day}/{event_id}.json` pattern
    - _Requirements: Requirement 9.6, NFR-2.1_


- [ ] 10. Lifecycle scheduler and expiry enforcement
  - [ ] 10.1 Implement the lifecycle service
    - Create `app/services/lifecycle.py` with `LifecycleService` class
    - Implement `calculate_due_actions(expiry_date: date, current_date: date, config: LifecycleConfig) -> set[LifecycleAction]` — pure function implementing the lifecycle action calculator logic; return the correct set of `LifecycleAction` enum values: `SEND_WARNING_14D`, `SEND_WARNING_7D`, `SET_EXPIRY_PENDING`, `SEND_FINAL_WARNING`, `TRIGGER_DEPROVISION` based on the day delta and config flags (see Property 14 specification)
    - Implement `run_daily_lifecycle_check(current_date: date)` — query `resource_inventory` for all active and expiry_pending resources; for each, call `calculate_due_actions`; dispatch the appropriate SNS notifications and status transitions
    - Implement SNS email notification dispatch using boto3 SNS publish with templates for each lifecycle event
    - _Requirements: NFR-12.1–12.9_

  - [ ]* 10.2 Write property test for lifecycle action calculator
    - **Property 14: Lifecycle scheduler correctly identifies due actions**
    - **Validates: Requirements NFR-12.1, NFR-12.2, NFR-12.3, NFR-12.5, NFR-12.6**
    - Use Hypothesis `@given(expiry_date=st.dates(), current_date=st.dates())` across the full calendar date space
    - Assert the correct action set returned for each milestone date; assert empty set for all non-milestone dates; use parameterised lifecycle config to test non-default values
    - _Tag: `# Feature: aws-developer-platform, Property 14: Lifecycle scheduler correctly identifies due actions`_

  - [ ] 10.3 Implement the lifecycle HTTP endpoint and EventBridge wiring
    - Add `GET /internal/lifecycle/run` endpoint (protected by internal API key) that calls `LifecycleService.run_daily_lifecycle_check(date.today())`; return a summary of actions taken
    - Create `terraform/modules/platform_infra/eventbridge.tf` — define `aws_scheduler_schedule` resource with `cron(0 1 * * ? *)` targeting the ECS task on `platform-cluster` with `LIFECYCLE_RUN=true` environment variable override
    - _Requirements: NFR-12_

  - [ ]* 10.4 Write unit tests for lifecycle service
    - Test T-14: correct SNS notification sent, `warning_14d_sent_at` updated
    - Test T-0: status transitions to `expiry_pending`, deployer policy update blocked
    - Test T+30 with `auto_deprovision_enabled=True`: deprovision TFC run triggered
    - Test T+30 with `auto_deprovision_enabled=False`: no TFC run, Platform_Admin notified
    - _Requirements: NFR-12.1–12.8_


- [ ] 11. Cost estimation and budget/quota checks
  - [ ] 11.1 Implement the cost estimator service
    - Create `app/services/cost_estimator.py` with `CostEstimatorService` class
    - Implement `estimate_lambda(memory_mb: int, duration_seconds: float, invocations: int) -> Decimal` — apply formula: `(invocations × duration_seconds × memory_mb/1024 × 0.0000166667) + (invocations × 0.0000002)` using current pricing from AWS Pricing API; cache rates at startup (5-minute TTL); if Pricing API unavailable use cached rates and set `stale=True`
    - Implement `estimate_dynamodb_ondemand(read_requests: int, write_requests: int, region: str) -> Decimal` — fetch per-RRU and per-WRU pricing from AWS Pricing API
    - Implement `estimate_dynamodb_provisioned(rcu: int, wcu: int, region: str) -> Decimal` — apply `rcu × $0.00013/hour × 730 + wcu × $0.00065/hour × 730`
    - Implement `estimate_s3(storage_gb: float, region: str) -> Decimal` — use 10 GB default; return cost with `disclaimer=True`
    - Add `GET /cost/estimate` endpoint proxying these functions for real-time frontend updates
    - _Requirements: NFR-3.1–3.5_

  - [ ]* 11.2 Write property test for cost estimation
    - **Property 10: Cost estimation is non-negative and formula-correct**
    - **Validates: NFR-3.1, NFR-3.3**
    - Use Hypothesis with `memory_mb > 0`, `duration_seconds > 0`, `invocations ≥ 0` (and equivalents for other resource types)
    - Assert every returned cost is ≥ 0; assert result matches reference formula within $0.01 tolerance; assert no exception raised for any valid input
    - _Tag: `# Feature: aws-developer-platform, Property 10: Cost estimation is non-negative and formula-correct`_

  - [ ] 11.3 Implement budget check service
    - Create `app/services/budget_checker.py` with `BudgetChecker` class
    - Implement `check_budget(project_id: UUID, new_request_cost: Decimal, db: AsyncSession) -> BudgetCheckResult` — query `resource_inventory` to sum `estimated_monthly_cost_usd` for all active resources in the project; add `new_request_cost`; compare against project's `monthly_budget_usd`; return `BudgetCheckResult(requires_exception: bool, current_spend, projected_total, limit, overage)`
    - Wire into `POST /requests` — after guardrail evaluation, call `BudgetChecker.check_budget`; if `requires_exception=True`, transition status to `budget_review`
    - _Requirements: NFR-4.1–4.8_

  - [ ]* 11.4 Write property test for budget check
    - **Property 11: Budget check decision is correct**
    - **Validates: NFR-4.1, NFR-4.2, NFR-4.3**
    - Use Hypothesis with `current_spend ≥ 0`, `new_cost ≥ 0`, `limit > 0`
    - Assert `requires_exception == True` iff `current_spend + new_cost > limit`; assert never returns True when within limit
    - _Tag: `# Feature: aws-developer-platform, Property 11: Budget check decision is correct`_

  - [ ] 11.5 Implement quota check service
    - Create `app/services/quota_checker.py` with `QuotaChecker` class
    - Implement `check_quota(project_id: UUID, environment: str, resource_type: str, db: AsyncSession) -> QuotaCheckResult` — count provisioned resources matching (project, environment, resource_type) in `resource_inventory`; compare against `platform_config` quota for that type; return `QuotaCheckResult(requires_exception: bool, current_count, limit, source)`
    - Wire into `POST /requests` — after budget check, call `QuotaChecker.check_quota`; if `requires_exception=True`, transition to `quota_review`
    - _Requirements: NFR-6.1–6.6_

  - [ ]* 11.6 Write property test for quota check
    - **Property 12: Quota check decision is correct**
    - **Validates: NFR-6.1, NFR-6.2**
    - Use Hypothesis with `current_count ≥ 0`, `quota_limit > 0`
    - Assert `requires_exception == True` iff `current_count + 1 > quota_limit`; assert False when within quota
    - _Tag: `# Feature: aws-developer-platform, Property 12: Quota check decision is correct`_

  - [ ] 11. Checkpoint — Ensure all tests pass, ask the user if questions arise.


- [ ] 12. Platform administration, config sync, and security middleware
  - [ ] 12.1 Implement the config sync service
    - Create `app/services/config_sync.py` with `ConfigSyncService` class
    - Implement `sync_from_repo(github_token: str, repo: str)` — pull YAML files from the seven config directories in `platform-config` using GitHub API (`GET /repos/{owner}/{repo}/contents/{path}`); upsert each entry into `platform_config` table with `source_path` and `source_commit`; update in-memory config cache
    - Implement `get_cached(config_type: str, config_key: str) -> Any` — read from in-memory cache with fallback to `platform_config` table
    - Add `POST /admin/config/sync` webhook endpoint — verify GitHub webhook signature (HMAC-SHA256 on `X-Hub-Signature-256`); trigger `sync_from_repo` as a background task
    - Add startup sync: call `sync_from_repo` on FastAPI `startup` event
    - Add 5-minute polling fallback as a FastAPI background task; compare latest commit SHA before syncing
    - _Requirements: NFR-1.1–1.4, Requirement 10.3_

  - [ ] 12.2 Implement the admin router for dropdown and guardrail management
    - Create `app/routers/admin.py`
    - `GET /admin/config/{config_type}` — return current values for dropdowns, guardrail enabled states, quotas (Platform_Admin only)
    - `PATCH /admin/config/dropdowns/cost-centers` — update `cost_center` allowed values in `platform_config` and commit change to `platform-config` repo via GitHub API (create branch, commit YAML update, open PR); emit `admin.config_changed` audit event
    - `PATCH /admin/guardrails/{rule_id}` — toggle a guardrail rule's `enabled` flag; commit to config repo; emit audit event
    - All admin endpoints enforce Platform_Admin role via middleware
    - _Requirements: Requirement 4.5, Requirement 10.1, 10.2, 10.3_

  - [ ] 12.3 Implement rate limiting middleware
    - Create `app/middleware/rate_limiter.py` — sliding window rate limiter using in-memory `dict` (suitable for single ECS task; note in code that Redis would be needed for multi-task consistency)
    - Enforce limits from `platform_config`: 5 resource submissions/min/user, 30 general API calls/min/user, 3 project registrations/hour/Team_Lead, 10 admin config changes/hour/Platform_Admin, 100 total requests/min platform-wide
    - On breach: return HTTP 429 with `Retry-After` header and human-readable message; emit `security.rate_limit_breach` audit event (non-blocking background task)
    - _Requirements: NFR-9.1–9.5_

  - [ ] 12.4 Implement security monitoring and alerting
    - Create `app/services/security_monitor.py`
    - Track consecutive failed auth attempts per user identity (in-memory counter with 10-minute window); emit SNS alert + audit event after 5 failures (per NFR-11.1)
    - Detect Developer attempting `staging`/`prod` environment: emit `security.privilege_escalation_attempt` audit event after 403 response
    - Detect off-hours Terraform runs: after triggering any TFC run, check if current time is outside Monday–Friday 07:00–20:00 local time; if so emit `security.off_hours_run` audit event + SNS alert
    - Detect bulk request anomaly: track per-user request count in rolling 1-hour window; emit alert if count exceeds 20 (per NFR-11.1)
    - Emit all security events as dual-write audit events via `AuditLogger`
    - _Requirements: NFR-11.1–11.3_

  - [ ]* 12.5 Write property test for RBAC completeness
    - **Property 2: Role-based access control is total and correct**
    - **Validates: Requirement 1.5**
    - Use Hypothesis to generate all combinations of `(route, http_method, user_role)` from the platform's defined route list and role set
    - Assert the RBAC check function returns a deterministic allow/deny decision matching the specification table; assert no unhandled exception for any combination
    - _Tag: `# Feature: aws-developer-platform, Property 2: Role-based access control is total and correct`_

  - [ ]* 12.6 Write property test for identity extraction completeness
    - **Property 1: Identity extraction completeness**
    - **Validates: Requirement 1.3**
    - Use Hypothesis to generate arbitrary IAM role tag maps with `display_name`, `email`, and `team` keys in any order and with arbitrary valid string values
    - Assert the identity extraction function returns a non-null object with all three fields populated from the corresponding tag values
    - _Tag: `# Feature: aws-developer-platform, Property 1: Identity extraction completeness`_


- [ ] 13. React SPA — core shell, routing, and auth flow
  - [ ] 13.1 Initialise the React SPA project
    - Bootstrap with Vite + React 18 + TypeScript; install MUI v5, TanStack Query v5, Zustand, React Router v6, AWS SDK for JavaScript v3 (`@aws-sdk/client-sts`)
    - Create top-level routing structure in `src/App.tsx` with routes matching the design's route table: `/login`, `/dashboard`, `/requests/new`, `/requests/:id`, `/approvals`, `/projects`, `/projects/new`, `/projects/:id`, `/admin`, `/admin/audit`, `/admin/cost`
    - Implement `ProtectedRoute` component: redirect to `/login` if no valid session in Zustand store
    - Implement role-based `ProtectedRoute` variant: render 403 page if user role does not have access to the route
    - _Requirements: Requirement 1.5_

  - [ ] 13.2 Implement the auth flow and session management in the SPA
    - Create `src/pages/Login.tsx` — use AWS SDK `STSClient.assumeRole()` to obtain temporary credentials; submit credentials to `POST /auth/session`; on success store `{role, team, display_name, session_expires_at}` in Zustand `sessionStore`
    - Create `src/store/session.ts` (Zustand) with: `user`, `sessionExpiresAt`, `lastActivityAt`, `idleCountdown`; implement idle timer that updates `lastActivityAt` on user interaction events (mousemove, keydown, click)
    - Implement session expiry warning modal: at `idleTimeout - warningThreshold` (default 5 min), display a modal warning with countdown; offer "Stay signed in" and "Sign out" buttons
    - Implement session draft save: when warning modal is shown and a request form is open, display an additional warning and auto-save form values to `localStorage`
    - _Requirements: NFR-8.1–8.6_

  - [ ] 13.3 Implement the dashboard page
    - Create `src/pages/Dashboard.tsx` — use TanStack Query to fetch `GET /requests` for the authenticated user; render a MUI `DataGrid` with columns: ID, resource type, resource name, status (coloured chip), environment, submitted date, expiry date
    - Status chip colours: pending/guardrail_review (amber), approval_pending (blue), approved (light green), provisioning (blue pulse), provisioned (green), failed (red), expired (grey), expiry_pending (orange), rejected (red), deprovisioned (grey)
    - Include filter controls: status dropdown, date range picker; wire to query params on `GET /requests`
    - _Requirements: Requirement 8.1, 8.2, 8.3_


- [ ] 14. React SPA — resource request wizard
  - [ ] 14.1 Implement the multi-step resource request wizard shell
    - Create `src/pages/NewRequest/` directory with a wizard container component `NewRequestWizard.tsx`
    - Implement wizard step management in Zustand `requestFormStore.ts`: steps are `RESOURCE_TYPE`, `CONFIGURATION`, `COST_GUARDRAIL_REVIEW`, `SUBMIT`; store form values, current step, guardrail warnings received
    - Step 1: `ResourceTypeStep.tsx` — MUI card selector for S3, Lambda, DynamoDB with icons and descriptions
    - Step navigation: "Next" advances only when current step passes client-side validation; "Back" navigates without clearing data
    - _Requirements: Requirement 2.1, 2.2_

  - [ ] 14.2 Implement resource-specific configuration forms
    - Create `src/pages/NewRequest/S3ConfigForm.tsx` — fields: name suffix, region, block_public_access toggle, versioning toggle, encryption selector (SSE-S3/SSE-KMS), lifecycle policy toggle, logging toggle, plus all required tag fields (cost_center dropdown, environment dropdown, team dropdown, owner free-text pre-populated from project, project dropdown, application_name dropdown, expiry_date date picker defaulting to today+30)
    - Create `src/pages/NewRequest/LambdaConfigForm.tsx` — fields: name suffix, runtime dropdown, memory slider, timeout number, region, VPC toggle, reserved concurrency number, X-Ray toggle, environment variables table (each row has key, value-type toggle "Plaintext"/"Secret reference", value/path field); all required tag fields
    - Create `src/pages/NewRequest/DynamoDBConfigForm.tsx` — fields: name suffix, partition key name+type, optional sort key, billing mode radio, RCU/WCU (shown only when PROVISIONED), PITR toggle, TTL attribute name, table class radio, region; all required tag fields
    - Implement real-time naming preview component showing the fully constructed resource name as the user types
    - Wire `expiry_date` field: default to today+30, enforce max today+90 with client-side validation, display error message matching Requirement 4.15/4.16
    - _Requirements: Requirement 2.2, Requirement 3, Requirement 4, Requirement 12.1, Requirement 13.1, NFR-10.1, NFR-10.2_

  - [ ] 14.3 Implement cost estimation display and guardrail warning acknowledgement
    - Create `src/pages/NewRequest/CostGuardrailStep.tsx`
    - Use TanStack Query with `debounce(500ms)` to call `GET /cost/estimate` as form fields change; display estimated monthly cost prominently with the disclaimer text from NFR-3.4; if `stale=True` display staleness indicator
    - If projected cost exceeds budget, display budget warning with current spend, projected total, and overage; render a `budget_justification` textarea (min 20 chars) that must be filled before advancing
    - If quota would be exceeded, display quota warning with current count and limit; render a `quota_justification` textarea
    - Display all guardrail warnings as MUI `Alert` components; each warning must have an accompanying checkbox "I acknowledge this warning"; "Submit Request" button is disabled until all checkboxes are checked
    - _Requirements: Requirement 5.3, 5.4, NFR-3.1–3.5, NFR-4.2, NFR-4.3, NFR-6.1, NFR-6.2_

  - [ ] 14.4 Implement secret reference fields for Lambda environment variables
    - In `LambdaConfigForm.tsx`, for each environment variable row: render a toggle button group "Plaintext" / "Secret reference"
    - When "Secret reference" is selected: replace the value text field with a source selector (SSM Parameter Store / Secrets Manager) and a path text field
    - On form submit, include `type: "secret_reference"`, `source: "ssm"|"secrets_manager"`, `path: string` in the env var payload
    - _Requirements: NFR-10.1, NFR-10.2, NFR-10.3_

  - [ ] 14. Checkpoint — Ensure all tests pass, ask the user if questions arise.


- [ ] 15. React SPA — approval queue, project catalogue, and admin pages
  - [ ] 15.1 Implement the approval queue page
    - Create `src/pages/Approvals.tsx` — fetch `GET /approvals`; display pending requests in a MUI `Table` with columns: request ID, submitter, resource type, resource name, environment, estimated cost, guardrail warnings count, submitted date
    - For each row: "Approve" and "Reject" action buttons; clicking Reject opens a modal requiring a rejection reason text field
    - For `budget_review` items: display budget context (current spend, projected total, budget limit, justification text); "Approve Exception" and "Deny Exception" buttons
    - For `quota_review` items: same pattern with quota context
    - _Requirements: Requirement 6.1–6.5_

  - [ ] 15.2 Implement the project catalogue and registration pages
    - Create `src/pages/Projects.tsx` — fetch `GET /projects`; display as MUI cards with project name, team, status, and IAM role ARNs (if provisioned)
    - Create `src/pages/NewProject.tsx` — form with all fields from Requirement 14.1; multi-select for allowed environments and resource types; submit to `POST /projects`; show provisioning status badge while IAM roles are being created
    - Create `src/pages/ProjectDetail.tsx` — display project registration detail, IAM role ARNs with copy buttons, provisioned resource count per type, edit form for Team_Lead-editable fields, "Deactivate Project" button
    - _Requirements: Requirement 14.1–14.14_

  - [ ] 15.3 Implement the request detail page
    - Create `src/pages/RequestDetail.tsx` — fetch `GET /requests/{id}`; display all request fields, tags, guardrail warnings, status timeline (derived from `audit_events` for the request), provisioned ARN (if applicable), rejection reason (if rejected)
    - For requests in `expiry_pending`: display "Extend Expiry" button (Team_Lead only) with a date picker limited to today+90; display "Initiate Decommission" button
    - _Requirements: Requirement 8.4, NFR-12.3c, NFR-12.4_

  - [ ] 15.4 Implement the admin pages
    - Create `src/pages/Admin.tsx` — tabs: "Dropdowns", "Guardrails", "Cost", "Audit Log"
    - Dropdowns tab: editable lists for `cost_center` and `environment` values; "Save" triggers `PATCH /admin/config/dropdowns/cost-centers`
    - Guardrails tab: table of all guardrail rules with toggle switches for `enabled`; "Save" triggers `PATCH /admin/guardrails/{rule_id}`
    - Audit Log tab: filterable table fetching `GET /audit/events` with filters for category, actor, project, date range
    - Cost tab: display cost anomaly banners per project (fetching anomaly data); cross-team request list filterable by status, team, environment, date range
    - _Requirements: Requirement 10.1–10.3, NFR-5.3_


- [ ] 16. Property-based test suite
  - [ ] 16.1 Create the property test file and Hypothesis configuration
    - Create `tests/test_properties.py` with Hypothesis `@settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])` applied globally via `settings.register_profile`
    - Add `pytest.ini` or `pyproject.toml` test configuration: `testpaths = tests`, `asyncio_mode = auto`
    - Add `tests/conftest.py` with shared fixtures: async database session (testcontainers PostgreSQL), mock boto3 clients for STS/IAM/CloudWatch/S3, mock httpx client for TFC API calls
    - _Requirements: Design Testing Strategy_

  - [ ] 16.2 Implement remaining property tests not yet covered
    - Implement all property tests referenced in tasks 2.3, 3.2, 3.4, 4.2, 4.3, 5.5, 8.2, 9.3, 10.2, 11.2, 11.4, 11.6, 12.5, 12.6 in a single `tests/test_properties.py` file ensuring each has its `# Feature: aws-developer-platform, Property N: ...` comment tag
    - Run `pytest tests/test_properties.py` and confirm all 14 properties pass
    - _Requirements: All 14 correctness properties from design.md_

  - [ ] 16. Checkpoint — Ensure all property tests pass, ask the user if questions arise.

- [ ] 17. Integration tests
  - [ ] 17.1 Implement integration tests for the full request submission flow
    - Create `tests/integration/test_request_flow.py`
    - Test: submit request → guardrail evaluation → warnings attached → acknowledge warnings → moves to `approval_pending`
    - Test: full happy path from submission through approval to provisioned (mock TFC webhook)
    - Test: TFC webhook idempotency — send identical webhook twice, assert only one state transition
    - _Requirements: Requirement 2, 5, 6, 7_

  - [ ] 17.2 Implement integration tests for config sync and audit dual-write
    - Create `tests/integration/test_config_sync.py` — mock GitHub webhook payload with updated `cost_centers.yaml`; call `POST /admin/config/sync`; assert `platform_config` table updated and in-memory cache refreshed
    - Create `tests/integration/test_audit.py` — mock CloudWatch and S3 clients; trigger a state transition; assert both mocks received identical JSON payloads; assert `audit_events` table contains corresponding row
    - _Requirements: Requirement 9, NFR-1, NFR-2_

  - [ ] 17.3 Implement integration tests for session creation and expiry
    - Create `tests/integration/test_auth.py`
    - Test: valid STS credentials → JWT cookie set → protected endpoint accessible
    - Test: expired JWT → 401 returned on protected endpoint
    - Test: session idle timeout logic via `session_middleware` unit-level test with mocked timestamps
    - _Requirements: Requirement 1, NFR-8_

  - [ ] 17. Final checkpoint — Ensure all tests pass, ask the user if questions arise.


---

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP build; remove the `*` to include them in execution
- Each task references specific requirements and NFRs for full traceability
- Checkpoints at epic boundaries ensure incremental validation before moving forward
- Property tests (Property 1–14) validate the core correctness invariants using Hypothesis with 200 examples per property
- The IAM policy builder (task 8.1) must be implemented before project onboarding (task 8.3) — the deployer, developer, and readonly policies are generated at project registration time
- The config sync service (task 12.1) must be implemented before the guardrail engine rule loading (task 5.1) — guardrail enabled states are read from `platform_config` populated by the sync
- The React SPA assumes the FastAPI backend is running on `http://localhost:8000` in development (configure via `VITE_API_BASE_URL` environment variable)
- Terraform modules (in `platform-config` repo) are separate from this codebase; tasks 1.2 and 10.3 reference the EventBridge scheduler Terraform resource but the full IaC implementation lives in the config repo
- The `platform-config` repo structure is defined in the design; Terraform modules under `terraform/modules/` are provisioned separately and are not part of the FastAPI or React implementation tasks


## Task Dependency Graph

```json
{
  "waves": [
    {
      "id": 0,
      "tasks": ["1.1", "1.3"]
    },
    {
      "id": 1,
      "tasks": ["1.2"]
    },
    {
      "id": 2,
      "tasks": ["3.1", "3.3", "9.1", "13.1"]
    },
    {
      "id": 3,
      "tasks": ["2.1", "3.2", "3.4", "9.2", "12.3"]
    },
    {
      "id": 4,
      "tasks": ["2.2", "4.1", "5.1", "12.1"]
    },
    {
      "id": 5,
      "tasks": ["2.3", "2.4", "4.2", "4.3", "5.2", "5.3", "5.4", "8.1", "12.4", "13.2"]
    },
    {
      "id": 6,
      "tasks": ["4.4", "5.5", "5.6", "6.1", "7.1", "8.2", "9.3", "9.4", "12.2", "12.5", "12.6", "13.3"]
    },
    {
      "id": 7,
      "tasks": ["6.2", "6.3", "7.2", "8.3", "11.1", "14.1"]
    },
    {
      "id": 8,
      "tasks": ["7.3", "8.4", "10.1", "11.2", "11.3", "14.2"]
    },
    {
      "id": 9,
      "tasks": ["10.2", "10.3", "11.4", "11.5", "14.3", "14.4"]
    },
    {
      "id": 10,
      "tasks": ["10.4", "11.6", "15.1", "15.2", "15.3"]
    },
    {
      "id": 11,
      "tasks": ["15.4", "16.1"]
    },
    {
      "id": 12,
      "tasks": ["16.2"]
    },
    {
      "id": 13,
      "tasks": ["17.1", "17.2", "17.3"]
    }
  ]
}
```

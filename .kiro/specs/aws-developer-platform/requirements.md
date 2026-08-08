# Requirements Document

## Introduction

This document defines the requirements for the AWS Developer Platform — a proof-of-concept (POC) internal developer portal that enables developers of mixed technical backgrounds to self-service provision AWS resources (S3 buckets, Lambda functions, and DynamoDB tables) through a web UI. The platform enforces governance guardrails, required resource tagging, naming conventions, and a lightweight approval workflow backed by Terraform Cloud for actual resource provisioning.

---

## Glossary

- **Portal**: The web-based internal developer portal through which users interact with the platform.
- **Developer**: A platform user who submits resource provisioning requests.
- **Approver**: A manager or team lead responsible for approving or rejecting provisioning requests.
- **Platform_Admin**: A privileged user who can view all requests across all teams and manage platform configuration.
- **Request**: A developer's submission to provision an AWS resource, including all required parameters and tags.
- **Resource**: An AWS cloud resource managed by the platform (S3 bucket, Lambda function, or DynamoDB table).
- **Guardrail**: A policy rule that enforces AWS best practices or organizational standards on a resource request.
- **Tag**: A key-value metadata pair attached to an AWS resource for governance, cost allocation, and ownership tracking.
- **Approval_Queue**: The list of pending requests visible to an Approver in the portal.
- **Terraform_Cloud**: The third-party CI/CD-like service used to apply infrastructure changes via Terraform runs.
- **IAM_Role**: An AWS Identity and Access Management role used to authenticate and authorize platform users. Each user assumes a designated IAM role to access the Portal.
- **Team_Lead**: A privileged user role above Developer. Team Leads can register projects, promote resources to `staging` and `prod` environments, and approve provisioning requests on behalf of their team.
- **Project_Registration**: The administrative act of a Team_Lead creating a project record in the platform, which seeds dropdown values, enables allowed environments, and pre-creates IAM scaffolding for the project.
- **Developer_Role (project-level)**: A project-specific IAM role named `{projectname}-developer`, created during project registration, granting read-only access to the project's running resources for developers and tooling.
- **Readonly_Role**: A project-specific IAM role named `{projectname}-readonly`, created during project registration, granting consumer-level read access to the project's running resources for external applications and services.
- **Deployer_Role**: A project-specific IAM role named `{projectname}-deployer`, created at project registration time (see Requirement 14), granting least-privilege permissions to deploy resources belonging to that project. Its IAM policy is updated incrementally as new resources are provisioned under the project.
- **Config_Repo**: A Git repository (e.g., `platform-config`) that stores platform configuration as code — including guardrail rules, allowed dropdown values, project definitions, resource quotas, and cost limits. Changes to platform configuration are made via pull requests; the commit history serves as the administrative change audit trail. Terraform Cloud watches the repo and applies changes on merge.
- **Audit_Logger**: The platform component responsible for writing structured audit events to both CloudWatch Logs and the immutable S3 audit bucket simultaneously (dual-write pattern).
- **Naming_Convention**: The required format for resource names, which varies by resource type:
  - **S3 bucket**: `{team}-{project}-{environment}-{name}` — lowercase alphanumeric and hyphens only; max 63 characters.
  - **Lambda function**: `{team}-{project}-{environment}-{name}` — lowercase alphanumeric and hyphens only; max 64 characters; must not start with `aws-`.
  - **DynamoDB table**: `{team}.{project}.{environment}.{name}` — alphanumeric, hyphens, underscores, and dots permitted; max 255 characters; the `name` segment should be PascalCase (e.g., `UserSessions`).
  - Note: `dev` and `uat` are developer-accessible environments. `staging` and `prod` are team-lead-restricted environments.

---

## Requirements

### Requirement 1: User Authentication

**User Story:** As a user, I want to authenticate to the Portal by assuming a designated AWS IAM role, so that my identity is known to the platform and my team and ownership information can be used automatically.

#### Acceptance Criteria

1. WHEN a user accesses the Portal, THE Portal SHALL verify that the user has assumed an authorised AWS IAM_Role before granting access.
2. WHEN a user successfully assumes an authorised IAM_Role, THE Portal SHALL establish a session for that user.
3. WHEN a session is established, THE Portal SHALL extract the user's identity attributes (name, email, team) from the IAM_Role's session context or associated role tags.
4. IF an IAM_Role assumption attempt fails or the assumed role is not authorised, THEN THE Portal SHALL display an error message and deny access.
5. WHILE a user's session is active, THE Portal SHALL enforce role-based access so that Developers, Approvers, and Platform_Admins see only the views and actions permitted to their role.

---

### Requirement 2: Resource Request Submission

**User Story:** As a Developer, I want to submit a request to create an AWS resource (S3 bucket, Lambda function, or DynamoDB table) through the Portal, so that I can provision cloud resources without needing direct AWS console access.

#### Acceptance Criteria

1. WHEN a Developer initiates a new resource request, THE Portal SHALL present a resource type selector allowing the Developer to choose between S3, Lambda, and DynamoDB.
2. WHEN a Developer selects a resource type, THE Portal SHALL present a form with fields contextual to that resource type, including the resource name suffix, region, and all required and optional tags.
3. WHEN a Developer submits a request, THE Portal SHALL validate that all required fields are present and non-empty before accepting the submission.
4. WHEN a Developer submits a request, THE Portal SHALL auto-populate the `created_by` tag with the authenticated user's identity from the IAM_Role session context.
5. WHEN a Developer submits a request, THE Portal SHALL record the request with a status of `pending` and assign it a unique request ID.
6. IF a Developer submits a request with any required field missing, THEN THE Portal SHALL reject the submission and indicate which fields are missing.

---

### Requirement 3: Resource Naming Convention Enforcement

**User Story:** As a Platform_Admin, I want all provisioned resource names to follow a standard naming convention per resource type, so that resource ownership and purpose are immediately identifiable.

#### Acceptance Criteria

**S3 Buckets:**

1. THE Portal SHALL construct the full S3 bucket name as `{team}-{project}-{environment}-{name}` using tag values supplied in the request.
2. WHEN a Developer enters a bucket name suffix (`name` segment), THE Portal SHALL validate that the suffix contains only lowercase alphanumeric characters and hyphens.
3. WHEN a Developer enters a bucket name suffix that violates the allowed character set, THE Portal SHALL reject the submission and display the naming rule.
4. THE Portal SHALL enforce that the fully constructed bucket name does not exceed 63 characters in total length.
5. IF the fully constructed bucket name would exceed 63 characters, THEN THE Portal SHALL reject the submission and display the length constraint.
6. THE Portal SHALL enforce that the fully constructed bucket name does not start or end with a hyphen.
7. IF the fully constructed bucket name starts or ends with a hyphen, THEN THE Portal SHALL reject the submission and display the hyphen boundary rule.

**Lambda Functions:**

8. THE Portal SHALL construct the full Lambda function name as `{team}-{project}-{environment}-{name}` using tag values supplied in the request.
9. WHEN a Developer enters a Lambda function name suffix (`name` segment), THE Portal SHALL validate that the suffix contains only lowercase alphanumeric characters and hyphens.
10. WHEN a Developer enters a Lambda function name suffix that violates the allowed character set, THE Portal SHALL reject the submission and display the naming rule.
11. THE Portal SHALL enforce that the fully constructed Lambda function name does not exceed 64 characters in total length.
12. IF the fully constructed Lambda function name would exceed 64 characters, THEN THE Portal SHALL reject the submission and display the length constraint.
13. THE Portal SHALL enforce that the fully constructed Lambda function name does not start with the reserved prefix `aws-`.
14. IF the fully constructed Lambda function name starts with `aws-`, THEN THE Portal SHALL reject the submission and display the reserved prefix rule.

**DynamoDB Tables:**

15. THE Portal SHALL construct the full DynamoDB table name as `{team}.{project}.{environment}.{name}` using tag values supplied in the request.
16. WHEN a Developer enters a DynamoDB table name suffix (`name` segment), THE Portal SHALL validate that the suffix contains only alphanumeric characters, hyphens, underscores, and dots, and is formatted in PascalCase.
17. WHEN a Developer enters a DynamoDB table name suffix that violates the allowed character set or casing convention, THE Portal SHALL reject the submission and display the naming rule.
18. THE Portal SHALL enforce that the fully constructed DynamoDB table name does not exceed 255 characters in total length.
19. IF the fully constructed DynamoDB table name would exceed 255 characters, THEN THE Portal SHALL reject the submission and display the length constraint.

---

### Requirement 4: Required Tag Enforcement

**User Story:** As a Platform_Admin, I want every provisioned resource to carry a standard set of required tags, so that resources can be attributed to teams and cost centers for governance and billing.

#### Acceptance Criteria

1. THE Portal SHALL require the following tags on every resource request: `cost_center`, `environment`, `team`, `owner`, `project`, `application_name`, `expiry_date`.
2. WHEN presenting the resource request form, THE Portal SHALL offer `environment` as a dropdown with the values `dev`, `uat`, `staging`, and `prod`.
3. WHEN presenting the resource request form, THE Portal SHALL offer `cost_center` as a dropdown populated from a configurable list of allowed values managed by Platform_Admins.
4. THE Portal SHALL initialise the `cost_center` allowed values list with the following entries: "Engineering", "Trading", "Client Services", "Compliance".
5. THE Portal SHALL allow Platform_Admins to add, remove, or rename `cost_center` allowed values through the platform administration interface without a code deployment.
6. IF a submitted request contains a `cost_center` value not present in the current allowed list, THEN THE Portal SHALL reject the submission and display the set of currently permitted `cost_center` values.
7. WHEN presenting the resource request form, THE Portal SHALL offer `team` as a dropdown populated from the list of teams registered in the platform via Project_Registration. IF no projects have been registered for the Developer's accessible projects, THE Portal SHALL display a message indicating no projects are available.
8. WHEN presenting the resource request form, THE Portal SHALL offer `owner` as a required free-form text input. THE Portal SHALL pre-populate the `owner` field with the Team_Lead's identity from the selected project's registration record, which the Developer may override.
9. WHEN presenting the resource request form, THE Portal SHALL offer `project` as a dropdown populated from the list of projects registered in the platform that the Developer is authorised to access.
10. WHEN presenting the resource request form, THE Portal SHALL offer `application_name` as a dropdown populated from the `application_name` values defined in the registered projects accessible to the Developer.
11. WHEN a Developer submits a request, THE Portal SHALL auto-populate the `created_by` tag from the authenticated IAM_Role session identity and include it on the provisioned resource.
12. WHEN the resource request form is loaded, THE Portal SHALL default the `expiry_date` field to the current date plus 30 calendar days.
13. THE Portal SHALL allow the Developer to override the default `expiry_date` value before submitting the request.
14. WHEN a Developer submits a request, THE Portal SHALL validate that the supplied `expiry_date` is not more than 90 calendar days from the current date at the time of submission.
15. IF the supplied `expiry_date` exceeds the current date plus 90 calendar days, THEN THE Portal SHALL reject the submission and display the maximum expiry constraint.
16. IF the supplied `expiry_date` is in the past or equals the current date, THEN THE Portal SHALL reject the submission and display that the expiry date must be a future date.
17. THE Portal SHALL store and apply the `expiry_date` tag value to the provisioned AWS resource in ISO 8601 date format (YYYY-MM-DD).
18. IF a required tag is absent from a submitted request, THEN THE Portal SHALL reject the submission and list the missing tag keys.
19. WHEN a request is provisioned, THE Provisioner SHALL apply all required tags to the AWS resource via Terraform.

---

### Requirement 5: Guardrail Evaluation (Soft Warnings)

**User Story:** As a Platform_Admin, I want resource requests to be evaluated against AWS best-practice guardrails, so that developers are informed of policy concerns before a request is approved.

#### Acceptance Criteria

1. WHEN a Developer submits a resource request, THE Guardrail_Engine SHALL evaluate the request configuration against all defined guardrail rules applicable to the selected resource type.
2. WHEN a guardrail rule is violated, THE Guardrail_Engine SHALL attach a warning to the request describing the violated rule and the recommended remediation.
3. THE Portal SHALL display all guardrail warnings to the Developer on the request confirmation screen before the request is submitted for approval.
4. WHEN a request has one or more guardrail warnings, THE Portal SHALL require the Developer to explicitly acknowledge each warning before the request proceeds to the Approval_Queue.
5. THE Platform SHALL record all guardrail warnings and the Developer's acknowledgement in the request audit trail.
6. THE Portal SHALL NOT allow a Developer to override a guardrail without acknowledgement; override-without-justification is not supported in this POC.

**S3 Guardrail Rules:**

7. THE Guardrail_Engine SHALL evaluate S3 bucket requests against the following named rules:
   - **S3-G1: Public Access** — WHEN an S3 request does not explicitly enable S3 Block Public Access settings, THE Guardrail_Engine SHALL attach a warning identifying rule S3-G1.
   - **S3-G2: Versioning** — WHEN an S3 request does not enable versioning, THE Guardrail_Engine SHALL attach a warning identifying rule S3-G2.
   - **S3-G3: Encryption** — WHEN an S3 request does not configure server-side encryption (SSE-S3 or SSE-KMS), THE Guardrail_Engine SHALL attach a warning identifying rule S3-G3.
   - **S3-G4: Lifecycle Policy** — WHEN an S3 request does not specify a lifecycle policy, THE Guardrail_Engine SHALL attach a warning identifying rule S3-G4 and recommend a minimum 90-day transition to S3-IA or Glacier for dev/uat environments.
   - **S3-G5: Logging** — WHEN an S3 request does not enable S3 server access logging, THE Guardrail_Engine SHALL attach a warning identifying rule S3-G5.

**Lambda Guardrail Rules:**

8. THE Guardrail_Engine SHALL evaluate Lambda function requests against the following named rules:
   - **L-G1: Memory Limit** — WHEN a Lambda request for a dev or uat environment specifies memory exceeding 512 MB, THE Guardrail_Engine SHALL attach a warning identifying rule L-G1.
   - **L-G2: Timeout** — WHEN a Lambda request for a dev or uat environment specifies a timeout exceeding 30 seconds, THE Guardrail_Engine SHALL attach a warning identifying rule L-G2.
   - **L-G3: Concurrency** — WHEN a Lambda request does not set reserved concurrency, THE Guardrail_Engine SHALL attach a warning identifying rule L-G3 and recommend a reserved concurrency of 10 or fewer for dev/uat environments.
   - **L-G4: Runtime** — WHEN a Lambda request specifies a deprecated or end-of-life runtime (e.g., python3.8, nodejs14.x), THE Guardrail_Engine SHALL attach a warning identifying rule L-G4.
   - **L-G5: VPC** — WHEN a Lambda request does not attach the function to a VPC, THE Guardrail_Engine SHALL attach a warning identifying rule L-G5.
   - **L-G6: Tracing** — WHEN a Lambda request does not enable AWS X-Ray active tracing, THE Guardrail_Engine SHALL attach a warning identifying rule L-G6.
   - **L-G7: Environment Variables** — WHEN a Lambda request includes environment variable values matching patterns indicative of secrets (containing the substrings `SECRET`, `PASSWORD`, `TOKEN`, or `KEY` in the variable name), THE Guardrail_Engine SHALL attach a warning identifying rule L-G7.

**DynamoDB Guardrail Rules:**

9. THE Guardrail_Engine SHALL evaluate DynamoDB table requests against the following named rules:
   - **D-G1: Billing Mode** — WHEN a DynamoDB request for a dev or uat environment selects provisioned capacity mode, THE Guardrail_Engine SHALL attach a warning identifying rule D-G1 and recommend on-demand (PAY_PER_REQUEST) mode.
   - **D-G2: Provisioned Capacity Limits** — WHEN a DynamoDB request uses provisioned capacity mode and specifies read capacity units (RCU) exceeding 25 or write capacity units (WCU) exceeding 25 for a dev or uat environment, THE Guardrail_Engine SHALL attach a warning identifying rule D-G2.
   - **D-G3: Point-in-Time Recovery** — WHEN a DynamoDB request does not enable Point-in-Time Recovery (PITR), THE Guardrail_Engine SHALL attach a warning identifying rule D-G3.
   - **D-G4: Encryption** — WHEN a DynamoDB request does not enable server-side encryption with an AWS-managed key, THE Guardrail_Engine SHALL attach a warning identifying rule D-G4.
   - **D-G5: TTL** — WHEN a DynamoDB request for a dev or uat environment does not configure a Time-to-Live (TTL) attribute, THE Guardrail_Engine SHALL attach a warning identifying rule D-G5.
   - **D-G6: Table Class** — WHEN a DynamoDB request does not consider the STANDARD_INFREQUENT_ACCESS table class for infrequently accessed data, THE Guardrail_Engine SHALL attach a warning identifying rule D-G6.

---

### Requirement 6: Approval Workflow

**User Story:** As an Approver, I want to review and act on pending resource requests through the Portal, so that I can ensure requests are appropriate before resources are created.

#### Acceptance Criteria

1. WHEN a Developer's request is submitted and all required fields pass validation, THE Portal SHALL place the request in the Approval_Queue for the Developer's assigned Approver.
2. WHEN an Approver logs into the Portal, THE Portal SHALL display the Approval_Queue showing all requests pending that Approver's review.
3. WHEN an Approver approves a request, THE Portal SHALL update the request status to `approved` and trigger the provisioning workflow.
4. WHEN an Approver rejects a request, THE Portal SHALL update the request status to `rejected` and record the Approver's rejection reason.
5. THE Portal SHALL display the rejection reason to the Developer when they view a rejected request.
6. WHEN a pending request has not been acted upon within 7 days, THE Portal SHALL automatically update the request status to `expired`.
7. WHEN a request expires, THE Portal SHALL notify the Developer that the request has expired and must be re-submitted if still needed.

---

### Requirement 7: Terraform Cloud Provisioning Integration

**User Story:** As a Platform_Admin, I want approved requests to be automatically provisioned by calling the Terraform Cloud API, so that resource creation is consistent and auditable without manual intervention.

#### Acceptance Criteria

1. WHEN a request transitions to `approved` status, THE Provisioner SHALL invoke the Terraform Cloud API to trigger a workspace run for the corresponding resource configuration (S3, Lambda, or DynamoDB as applicable).
2. WHEN the Terraform Cloud run is initiated, THE Provisioner SHALL pass all resource parameters as Terraform variables to the workspace run. The variables passed shall vary by resource type: S3 requests pass bucket name, region, and tags; Lambda requests pass function name, runtime, memory, timeout, VPC configuration, concurrency, tracing settings, environment variables, and tags; DynamoDB requests pass table name, key schema, billing mode, capacity settings, PITR toggle, TTL attribute, table class, and tags.
3. WHEN the Terraform Cloud run completes successfully, THE Provisioner SHALL update the request status to `provisioned`.
4. IF the Terraform Cloud run fails, THEN THE Provisioner SHALL update the request status to `failed` and record the error details from the Terraform Cloud run output.
5. THE Provisioner SHALL poll or receive callbacks from Terraform Cloud to track run status and update the request record accordingly.

---

### Requirement 8: Request Status Visibility

**User Story:** As a Developer, I want to track the status of my resource requests in the Portal, so that I know where each request stands in the workflow.

#### Acceptance Criteria

1. WHEN a Developer views the Portal, THE Portal SHALL display a list of all requests submitted by that Developer.
2. THE Portal SHALL display the current status of each request using one of the following states: `pending`, `approved`, `rejected`, `provisioning`, `provisioned`, `failed`, `expired`.
3. WHEN a request status changes, THE Portal SHALL reflect the updated status the next time the Developer views the request list or refreshes the page.
4. WHEN a Developer views an individual request, THE Portal SHALL display the full request details including all tags, resource configuration, guardrail warnings acknowledged, and the current status.

---

### Requirement 9: Audit Trail

**User Story:** As a Platform_Admin, I want every action on a request to be recorded with a timestamp and actor identity, so that there is a complete audit history for compliance and troubleshooting.

#### Acceptance Criteria

1. THE Platform SHALL record an audit log entry for every state transition of a request, including: `submitted`, `warning_acknowledged`, `approved`, `rejected`, `provisioning_started`, `provisioned`, `failed`, `expired`.
2. EACH audit log entry SHALL include: the request ID, the actor's identity (IAM_Role session principal), the action performed, and a UTC timestamp.
3. WHEN an Approver rejects a request, THE Audit_Logger SHALL record the rejection reason as part of the audit log entry.
4. WHEN a guardrail warning is acknowledged by a Developer, THE Audit_Logger SHALL record the acknowledged warning text in the audit log.
5. THE Platform SHALL retain audit log entries for a minimum of 90 days.
6. THE Platform SHALL write all audit log entries using a dual-write pattern: simultaneously to CloudWatch Logs (for real-time querying and dashboards) and to a dedicated S3 bucket with Object Lock enabled in Governance mode (for tamper-proof archival).
7. THE S3 audit bucket SHALL have Object Lock configured with a minimum retention period of 90 days; no user including Platform_Admins SHALL be able to delete or modify audit entries within the retention window.
8. THE S3 audit bucket SHALL have a lifecycle rule to transition audit objects to S3 Glacier after 90 days for long-term cost-efficient storage.
9. THE audit log SHALL cover not only request state transitions but also: administrative configuration changes (project edits, dropdown value changes, guardrail toggles), IAM role policy update events (recording which resource ARN was added, which request triggered it, and the UTC timestamp), and security events (failed authentication attempts, rate limit breaches, privilege escalation attempts, off-hours provisioning runs).
10. EACH audit log entry SHALL be written as a structured JSON object containing: event_type, request_id (if applicable), actor_identity (IAM_Role session principal), action, resource_arn (if applicable), timestamp (UTC ISO 8601), and source_ip.
11. THE Platform SHALL use the Config_Repo as the system of record for all platform configuration changes; the Git commit history of the Config_Repo SHALL serve as the immutable audit trail for administrative changes.

---

### Requirement 10: Platform Administration

**User Story:** As a Platform_Admin, I want visibility across all teams' requests and the ability to manage platform configuration, so that I can operate and troubleshoot the platform effectively.

#### Acceptance Criteria

1. WHEN a Platform_Admin logs into the Portal, THE Portal SHALL display a cross-team view of all resource requests, filterable by status, team, environment, and date range.
2. THE Portal SHALL allow Platform_Admins to manage the list of allowed values for both the `environment` and `cost_center` tag dropdowns, including adding, removing, and renaming entries without a code deployment.
3. THE Portal SHALL allow Platform_Admins to define and enable or disable individual guardrail rules without a code deployment.

---

### Requirement 11: On-Demand Deployer IAM Role Creation

**User Story:** As a Developer, I want a dedicated IAM deployer role to be created when my project is onboarded to the platform and kept up to date as resources are added, so that CI/CD pipelines and automation can deploy project resources using least-privilege credentials without sharing broad permissions.

#### Acceptance Criteria

1. WHEN a project is registered (per Requirement 14), THE Provisioner SHALL create the `{projectname}-deployer` IAM_Role as part of the project onboarding Terraform run.
2. WHEN the Deployer_Role is created, THE Provisioner SHALL attach an IAM policy granting least-privilege permissions scoped exclusively to the resources belonging to that project. The policy SHALL cover permissions for all resource types provisioned under the project — S3 bucket operations (`s3:GetObject`, `s3:PutObject`, `s3:DeleteObject`, `s3:ListBucket`, `s3:GetBucketLocation`, `s3:GetBucketTagging`, `s3:GetBucketVersioning`, `s3:GetBucketPolicy`, `s3:GetEncryptionConfiguration`, `s3:GetLifecycleConfiguration`, `s3:GetBucketLogging`) scoped to any provisioned S3 bucket ARNs; Lambda operations (`lambda:InvokeFunction`, `lambda:UpdateFunctionCode`, `lambda:GetFunction`, `lambda:GetFunctionConfiguration`, `lambda:GetPolicy`, `lambda:ListAliases`, `lambda:ListVersionsByFunction`, `lambda:GetFunctionConcurrency`, `lambda:ListTags`) scoped to any provisioned Lambda function ARNs; and DynamoDB operations (`dynamodb:GetItem`, `dynamodb:PutItem`, `dynamodb:Query`, `dynamodb:Scan`, `dynamodb:UpdateItem`, `dynamodb:DeleteItem`, `dynamodb:DescribeTable`, `dynamodb:DescribeTimeToLive`, `dynamodb:DescribeContinuousBackups`, `dynamodb:ListTagsOfResource`) scoped to any provisioned DynamoDB table ARNs, as applicable to the resources in that project.
3. WHEN the Deployer_Role is created, THE Provisioner SHALL apply the same required tags (`cost_center`, `environment`, `team`, `owner`, `project`, `application_name`) to the IAM role as are applied to the provisioned resource.
4. THE Deployer_Role is created during project registration (per Requirement 14), before any resource requests are made. Its IAM policy SHALL be updated each time a new resource is provisioned under the project, extending permissions to include the newly provisioned resource ARN. The role SHALL be available immediately upon resource creation.
5. WHEN the Terraform Cloud run that creates the Deployer_Role completes successfully, THE Provisioner SHALL record the Deployer_Role ARN in the request record and display it to the Developer in the request status view.
6. IF the Deployer_Role creation fails, THEN THE Provisioner SHALL update the request status to `failed` and record the IAM error details, treating the overall provisioning as unsuccessful.

---

### Requirement 12: Lambda Function Provisioning

**User Story:** As a Developer, I want to request provisioning of a Lambda function through the Portal, so that I can deploy serverless compute without needing direct AWS console access.

#### Acceptance Criteria

1. WHEN a Developer selects Lambda as the resource type, THE Portal SHALL present a form including the following fields: function name suffix, runtime (dropdown: python3.12, python3.11, nodejs20.x, nodejs18.x, java21, java17, dotnet8), memory in MB, timeout in seconds, region, VPC attachment (yes/no), reserved concurrency, X-Ray tracing toggle, environment variables (key-value pairs), and all required tags.
2. WHEN a Developer submits a Lambda function request, THE Portal SHALL validate the function name suffix against the Lambda Naming_Convention, rejecting submissions that violate character set rules, the 64-character length limit, or the `aws-` reserved prefix rule.
3. WHEN a Developer submits a Lambda function request, THE Portal SHALL auto-populate the `created_by` tag with the authenticated user's identity from the IAM_Role session context.
4. WHEN the Terraform Cloud run for a Lambda function request completes successfully, THE Provisioner SHALL record the provisioned Lambda function ARN in the request record and display it to the Developer in the request status view.
5. WHEN the Deployer_Role is created for a project containing a Lambda function, THE Provisioner SHALL include `lambda:InvokeFunction`, `lambda:UpdateFunctionCode`, `lambda:GetFunction`, `lambda:GetFunctionConfiguration`, `lambda:GetPolicy`, `lambda:ListAliases`, `lambda:ListVersionsByFunction`, `lambda:GetFunctionConcurrency`, and `lambda:ListTags` permissions in the Deployer_Role policy scoped to the provisioned function ARN.

---

### Requirement 13: DynamoDB Table Provisioning

**User Story:** As a Developer, I want to request provisioning of a DynamoDB table through the Portal, so that I can create managed NoSQL storage without needing direct AWS console access.

#### Acceptance Criteria

1. WHEN a Developer selects DynamoDB as the resource type, THE Portal SHALL present a form including the following fields: table name suffix, partition key name and type (String, Number, or Binary), optional sort key name and type (String, Number, or Binary), billing mode (on-demand or provisioned), read capacity units and write capacity units (displayed only when provisioned billing mode is selected), PITR toggle, TTL attribute name (optional), table class (STANDARD or STANDARD_IA), region, and all required tags.
2. WHEN a Developer submits a DynamoDB table request, THE Portal SHALL validate the table name suffix against the DynamoDB Naming_Convention, rejecting submissions that violate the allowed character set, the PascalCase convention for the name segment, or the 255-character length limit.
3. WHEN a Developer submits a DynamoDB table request, THE Portal SHALL auto-populate the `created_by` tag with the authenticated user's identity from the IAM_Role session context.
4. WHEN the Terraform Cloud run for a DynamoDB table request completes successfully, THE Provisioner SHALL record the provisioned DynamoDB table ARN in the request record and display it to the Developer in the request status view.
5. WHEN the Deployer_Role is created for a project containing a DynamoDB table, THE Provisioner SHALL include `dynamodb:GetItem`, `dynamodb:PutItem`, `dynamodb:Query`, `dynamodb:Scan`, `dynamodb:UpdateItem`, `dynamodb:DeleteItem`, `dynamodb:DescribeTable`, `dynamodb:DescribeTimeToLive`, `dynamodb:DescribeContinuousBackups`, and `dynamodb:ListTagsOfResource` permissions in the Deployer_Role policy scoped to the provisioned table ARN.

---

### Requirement 14: Project Onboarding and Setup

**User Story:** As a Team_Lead, I want to register a new project in the platform, so that my team has the correct IAM scaffolding, dropdown values, and environment permissions in place before developers begin requesting resources.

#### Acceptance Criteria

**Project Registration Form:**

1. WHEN a Team_Lead initiates a new project registration, THE Portal SHALL present a form with the following fields: project name, description, application name, team name, cost center (dropdown from platform-configured list), default owner (pre-populated with the Team_Lead's identity, overridable), allowed environments (multi-select from: `dev`, `uat`, `staging`, `prod` — but `staging` and `prod` selections SHALL require the registering user to hold the Team_Lead or Platform_Admin role), and allowed resource types (multi-select from: S3, Lambda, DynamoDB).
2. WHEN a Team_Lead submits a project registration, THE Portal SHALL validate that the project name contains only alphanumeric characters and hyphens and does not exceed 32 characters.
3. WHEN a Team_Lead submits a project registration, THE Portal SHALL validate that the project name is unique within the platform.
4. IF the project name is not unique, THEN THE Portal SHALL reject the registration and display the conflict.

**Environment Access Control:**

5. WHEN a Developer submits a resource request, THE Portal SHALL restrict the `environment` dropdown to only the environments enabled for the selected project.
6. WHEN a Developer submits a resource request, THE Portal SHALL enforce that Developers may only select `dev` or `uat` environments; IF a Developer attempts to submit a request for `staging` or `prod`, THEN THE Portal SHALL reject the submission with an authorisation error.
7. WHEN a Team_Lead or Platform_Admin submits a resource request, THE Portal SHALL allow selection of any environment enabled for the selected project, including `staging` and `prod`.

**IAM Scaffolding at Registration:**

8. WHEN a project registration is saved, THE Provisioner SHALL automatically create three IAM roles for the project via Terraform Cloud:
   a. `{projectname}-deployer` — least-privilege deploy permissions (as defined in Requirement 11) scoped to future project resources; initially created with a placeholder policy that will be updated as resources are provisioned.
   b. `{projectname}-developer` — read-only access to the project's running resources: `s3:GetObject`, `s3:ListBucket`, `s3:GetBucketLocation`, `s3:GetBucketTagging`, `lambda:GetFunction`, `lambda:GetFunctionConfiguration`, `lambda:ListAliases`, `lambda:ListTags`, `dynamodb:GetItem`, `dynamodb:Query`, `dynamodb:Scan`, `dynamodb:DescribeTable`, `dynamodb:ListTagsOfResource` — scoped to project resource ARNs as they are provisioned.
   c. `{projectname}-readonly` — consumer-level access for external applications: `s3:GetObject`, `lambda:InvokeFunction`, `dynamodb:GetItem`, `dynamodb:Query`, `dynamodb:Scan` — scoped to project resource ARNs as they are provisioned.
9. WHEN the IAM roles are created for a project registration, THE Provisioner SHALL tag all three roles with the project's `cost_center`, `team`, `project`, `application_name`, and `owner` tag values.
10. WHEN the project registration IAM run completes successfully, THE Portal SHALL display the ARNs for all three created IAM roles to the Team_Lead in the project detail view.
11. IF the IAM scaffolding run fails, THEN THE Portal SHALL mark the project registration as `iam_failed`, record the error, and alert the Team_Lead to retry or contact a Platform_Admin.

**Project Catalogue:**

12. WHEN a project is successfully registered, THE Portal SHALL make the project's name, team, and application_name available as selectable values in Developer resource request forms.
13. THE Portal SHALL allow Team_Leads to view and edit the project registration details (description, allowed environments, allowed resource types, default owner) after initial registration.
14. THE Portal SHALL allow Team_Leads to deactivate a project, which removes it from the Developer dropdown lists but does not delete provisioned resources.

---

## Non-Functional Requirements

### NFR-1: Configuration as Code

**Rationale**: Storing platform configuration in a Git repository provides a free, immutable change history via commits, enables PR-based review for configuration changes, and gives Terraform Cloud a clean IaC source of truth.

1. THE Platform SHALL store all mutable platform configuration in a designated Config_Repo, including: guardrail rule definitions and enabled/disabled states, allowed dropdown values (`cost_center`, `environment`), resource quota limits per project, cost budget thresholds, rate limit thresholds, expiry lifecycle parameters, and security alert thresholds.
2. WHEN a Platform_Admin makes a configuration change via the Portal administration interface, THE Platform SHALL commit the change to the Config_Repo via an automated PR and apply it on merge.
3. THE Platform SHALL use the Config_Repo commit history as the audit trail for all administrative configuration changes.
4. Terraform Cloud SHALL watch the Config_Repo and automatically apply infrastructure changes when configuration PRs are merged.

---

### NFR-2: Immutable Audit Logging

**Rationale**: The platform manages IAM roles, cost allocation, and sensitive provisioning operations. An immutable audit log is required for compliance, forensic investigation, and tamper-evidence. Dual-write to CloudWatch Logs and S3 with Object Lock satisfies both operational querying needs and compliance archival needs.

1. THE Platform SHALL implement a dual-write audit logging pattern: every audit event SHALL be written simultaneously to CloudWatch Logs (for real-time querying, dashboards, and alerting) and to a dedicated S3 bucket with Object Lock enabled in Governance mode (for tamper-proof archival).
2. THE S3 audit bucket SHALL be configured with Object Lock in Governance mode with a minimum retention period of 90 days. No user, including Platform_Admins and the AWS root account, SHALL be able to delete or overwrite audit entries within the retention window.
3. THE S3 audit bucket SHALL have a lifecycle rule configured to transition audit objects to S3 Glacier Instant Retrieval after 90 days for cost-efficient long-term storage.
4. THE audit log SHALL cover the following event categories:
   a. Request lifecycle events: all state transitions (submitted, approved, rejected, provisioning_started, provisioned, failed, expired, expiry_pending, deprovisioned).
   b. Administrative events: project registration, project edits, project deactivation, dropdown value changes, guardrail enable/disable, quota changes, budget threshold changes.
   c. IAM events: project IAM role creation, IAM policy updates (recording the added resource ARN, the triggering request ID, and UTC timestamp).
   d. Security events: failed authentication attempts, rate limit breaches, Developer attempts to access staging/prod environments, off-hours Terraform runs, bulk request anomalies, out-of-band IAM role policy changes.
   e. Cost events: budget threshold warnings, budget exception requests and approvals/denials, quota exception requests and approvals/denials, cost anomaly alerts.
   f. Lifecycle events: expiry warning notifications sent, expiry_pending status transitions, grace period warnings, auto-deprovision runs.
5. EACH audit log entry SHALL be a structured JSON object containing: `event_type`, `event_category`, `request_id` (if applicable), `project_name` (if applicable), `actor_identity` (IAM_Role session principal ARN), `action`, `resource_arn` (if applicable), `timestamp` (UTC ISO 8601), `source_ip`, and `additional_context` (a key-value map for event-specific details).

---

### NFR-3: Cost Estimation at Request Time

**Rationale**: Surfacing estimated costs at the point of request creates cost awareness before resources are provisioned, reducing bill surprises and encouraging developers to right-size resources.

1. WHEN a Developer configures a resource request form, THE Portal SHALL display a real-time estimated monthly cost for the configured resource, updated as form field values change.
2. THE Portal SHALL calculate cost estimates using the AWS Pricing API for the selected region and resource type.
3. Cost estimation SHALL cover:
   - **Lambda**: estimated monthly cost based on memory (MB), estimated invocation count (developer-supplied or defaulting to 10,000/month), and average duration (seconds). Formula: (invocations × duration_seconds × memory_GB × $0.0000166667) + (invocations × $0.0000002), updated per current AWS Pricing API rates.
   - **DynamoDB (on-demand)**: estimated monthly cost based on estimated read and write request units (developer-supplied or defaulting to 100,000 reads and 100,000 writes/month).
   - **DynamoDB (provisioned)**: estimated monthly cost based on RCU × $0.00013/hour and WCU × $0.00065/hour, updated per current AWS Pricing API rates.
   - **S3**: estimated monthly cost based on storage class and region with a displayed note: "Actual cost depends on stored data volume, request count, and data transfer. Estimate assumes 10 GB storage."
4. THE Portal SHALL display the cost estimate prominently on the request form with a disclaimer: "Estimated cost only. Actual charges depend on usage patterns."
5. THE Portal SHALL use the AWS Pricing API to retrieve current pricing at form load time; IF the Pricing API is unavailable, THE Portal SHALL display the last cached rates with a staleness indicator.

---

### NFR-4: Per-Project Monthly Budget Limits

**Rationale**: Configurable per-project budget limits prevent uncontrolled spend accumulation. A soft-limit model with mandatory justification and Team Lead approval balances cost governance with developer autonomy.

1. WHEN a Team_Lead registers a project (per Requirement 14), THE Portal SHALL allow the Team_Lead to set a monthly budget limit (in USD) for the project. IF no limit is set, THE Platform SHALL apply a default monthly budget limit of $100 USD per project.
2. WHEN a Developer submits a resource request, THE Portal SHALL calculate the sum of the estimated monthly costs of all currently provisioned resources in the project plus the estimated cost of the new request.
3. IF the projected total monthly cost would exceed the project's monthly budget limit, THEN THE Portal SHALL:
   a. Display the current budget, current estimated spend, and projected overage to the Developer.
   b. Require the Developer to enter a written justification (minimum 20 characters) explaining the business need for the budget exception.
   c. Place the request in a `budget_review` status in the Team Lead's review queue alongside the normal approval queue.
4. WHEN a Team_Lead reviews a budget exception request, THE Portal SHALL display the justification, current project spend, projected new total, and the budget limit.
5. THE Team_Lead SHALL be able to approve the budget exception (allowing the request to proceed to normal provisioning approval) or deny it (rejecting the request with a recorded reason).
6. IF a budget exception is denied, THE Portal SHALL notify the Developer and record the denial reason in the audit log.
7. THE Platform SHALL allow Platform_Admins to set a platform-wide maximum monthly spend ceiling. IF a project's projected spend would exceed the platform-wide ceiling, THE Portal SHALL hard-block the request and require a Platform_Admin (not just a Team_Lead) to raise the platform ceiling before the request can proceed.
8. THE monthly budget limit and platform-wide ceiling SHALL be configurable in the Config_Repo without a code deployment.

---

### NFR-5: AWS Cost Anomaly Detection Integration

**Rationale**: Actual AWS spend can diverge from estimates due to unexpected usage patterns (runaway Lambda invocations, high S3 egress, etc.). AWS Cost Anomaly Detection monitors real spend by tag and alerts when anomalies are detected, complementing the estimate-based budget limits.

**Default configuration (documented here; provisioned via IaC in Config_Repo at project registration time):**

1. WHEN a project is registered, THE Provisioner SHALL configure an AWS Cost Anomaly Detection monitor for the project, scoped by the `project` and `cost_center` tag dimensions.
2. THE anomaly monitor SHALL be configured with the following defaults:
   - Alert threshold: 20% above expected spend OR $50 above expected spend, whichever is lower — *rationale: catches meaningful spikes while avoiding noise from minor fluctuations.*
   - Evaluation frequency: daily — *rationale: daily checks balance detection speed with alert fatigue.*
   - Minimum anomaly duration: 1 day — *rationale: avoids false positives from one-off invocation spikes.*
   - Notification target: Team Lead email address (from project registration) via SNS.
3. WHEN a cost anomaly is detected for a project, THE Platform SHALL:
   a. Send an email alert to the project's Team Lead via SNS with the anomaly details (expected vs. actual spend, affected service, detection date).
   b. Write a cost anomaly audit event to the audit log (dual-write to CloudWatch Logs and S3).
   c. Display a cost anomaly banner on the project's dashboard in the Portal.
4. THE anomaly detection thresholds and notification targets SHALL be configurable per project in the Config_Repo without a code deployment.

---

### NFR-6: Per-Project Resource Quotas

**Rationale**: Raw resource count limits prevent runaway provisioning independent of cost. Using the same justification + Team Lead approval workflow as budget exceptions ensures consistency and auditability.

**Default quotas per project per environment (configurable in Config_Repo):**
- S3 buckets: 10 per project per environment
- Lambda functions: 10 per project per environment
- DynamoDB tables: 5 per project per environment

1. WHEN a Developer submits a resource request, THE Portal SHALL check the current count of provisioned resources of the same type for the selected project and environment against the configured quota.
2. IF the request would exceed the quota, THEN THE Portal SHALL:
   a. Display the current count, the quota limit, and the quota source (project-level or platform-wide).
   b. Require the Developer to enter a written justification (minimum 20 characters) explaining the business need for the quota exception.
   c. Place the request in a `quota_review` status in the Team Lead's review queue.
3. WHEN a Team_Lead reviews a quota exception request, THE Portal SHALL display the justification, current resource count, and quota limit.
4. THE Team_Lead SHALL be able to approve the quota exception (allowing the request to proceed) or deny it (rejecting with a recorded reason).
5. THE Platform SHALL allow Platform_Admins to set platform-wide maximum resource count ceilings per resource type that override project-level quotas. IF a project-level quota exception approval would cause the platform-wide ceiling to be exceeded, THE Portal SHALL hard-block the request and require a Platform_Admin to raise the platform-wide ceiling.
6. THE quota limits and platform-wide ceilings SHALL be configurable in the Config_Repo without a code deployment.

---

### NFR-7: Availability and Performance

**Rationale**: This is a POC for internal use. Targets are intentionally relaxed to reflect the development context while still setting meaningful baselines.

1. THE Portal SHALL target 99% uptime during business hours (Monday–Friday, 06:00–22:00 local time). No availability SLA applies outside business hours.
2. THE Portal SHALL render UI pages within 3 seconds under normal load (up to 50 concurrent users).
3. THE Portal's backend API SHALL respond to form submissions and status queries within 2 seconds under normal load.
4. WHEN a Terraform Cloud run has not completed within 30 minutes of being triggered, THE Platform SHALL mark the run as `stuck`, update the request status to `provisioning_warning`, and alert the Platform_Admin via SNS.
5. THE Platform SHALL retain request records for a minimum of 12 months before archival.

---

### NFR-8: Session Management

**Rationale**: The portal manages IAM roles and sensitive provisioning operations. Session timeout limits reduce the risk of unattended authenticated sessions. These defaults follow standard internal tool security guidelines (NIST SP 800-63B).

1. THE Portal SHALL invalidate a user session after 30 minutes of inactivity and redirect the user to re-authenticate. *Rationale: 30 minutes is the standard for internal tools handling sensitive operations — long enough for normal workflows, short enough to protect unattended sessions.*
2. THE Portal SHALL enforce a maximum absolute session length of 8 hours regardless of activity, forcing re-authentication at the 8-hour mark. *Rationale: prevents sessions from persisting across work days without IAM credential re-validation.*
3. WHEN a session is idle for 25 minutes (5 minutes before the 30-minute idle timeout), THE Portal SHALL display a session expiry warning to the user.
4. WHEN a user has an unsaved resource request form open and their session is approaching expiry, THE Portal SHALL warn the user that their session is about to expire and offer to save a draft.
5. WHEN a session expires due to inactivity, THE Portal SHALL require full IAM role re-assumption (not just a UI re-prompt), ensuring underlying AWS credentials are refreshed.
6. THE idle timeout (default: 30 minutes), absolute session limit (default: 8 hours), and warning threshold (default: 5 minutes before idle timeout) SHALL be configurable in the Config_Repo.

---

### NFR-9: API Rate Limiting

**Rationale**: Rate limiting protects the platform from accidental bulk submissions (e.g., a misconfigured CI/CD pipeline or scripted loop). Limits are intentionally conservative for a POC internal tool where human interaction is the primary use case. All thresholds are configurable.

**Default thresholds (configurable in Config_Repo; violations return HTTP 429 with Retry-After header and human-readable message; all violations logged to CloudWatch Logs):**

1. THE Portal API SHALL enforce the following per-user rate limits:
   - Resource request submissions: 5 per minute per user. *Rationale: a human cannot legitimately submit more than 5 requests per minute; higher rates indicate automation or error.*
   - General API calls (reads, status checks, form loads): 30 per minute per user. *Rationale: covers normal portal browsing and status polling without enabling scripted abuse.*
   - Project registrations: 3 per hour per Team_Lead. *Rationale: project registration is a deliberate administrative act, not a high-frequency operation.*
   - Admin configuration changes: 10 per hour per Platform_Admin. *Rationale: config changes are infrequent by nature; a high rate indicates a scripting error.*
2. THE Portal API SHALL enforce a platform-wide rate limit of 100 total API requests per minute across all users combined. *Rationale: protects backend infrastructure during unexpected load spikes.*
3. WHEN a rate limit is breached, THE Portal SHALL return HTTP 429 with a `Retry-After` header indicating when the user may retry, and a human-readable error message.
4. ALL rate limit breaches SHALL be written as security events to the audit log (dual-write to CloudWatch Logs and S3).
5. ALL rate limit thresholds SHALL be configurable in the Config_Repo without a code deployment.

---

### NFR-10: Secrets Management for Lambda Environment Variables

**Rationale**: Plaintext secrets in Lambda environment variables are a well-known security risk — they appear in Terraform state files, CloudTrail logs, and the Lambda console. SSM Parameter Store and Secrets Manager provide secure, auditable alternatives that Lambda natively supports via resolve syntax.

1. WHEN a Developer adds an environment variable to a Lambda function request, THE Portal SHALL offer a field type toggle for each variable: "Plaintext value" or "Secret reference".
2. WHEN "Secret reference" is selected, THE Portal SHALL present:
   - A source selector: AWS SSM Parameter Store or AWS Secrets Manager.
   - A path/name field for the parameter or secret path (e.g., `/myproject/dev/db-password`).
3. WHEN a Developer submits a Lambda request with one or more secret references, THE Portal SHALL validate that each referenced SSM parameter path or Secrets Manager secret name exists in the target AWS account before allowing submission. IF a referenced path does not exist, THE Portal SHALL reject the submission and identify the missing reference.
4. WHEN a Lambda function is provisioned with secret references, THE Provisioner SHALL configure the Lambda environment variables using the AWS native resolve syntax (`{{resolve:ssm:/path}}` or `{{resolve:secretsmanager:name}}`), ensuring plaintext values are never written to Terraform variables or state.
5. THE guardrail rule L-G7 SHALL only fire for environment variables configured as "Plaintext value" whose variable name matches a secret pattern; variables configured as "Secret reference" SHALL be exempt from L-G7.
6. WHEN a project's IAM roles (`-developer`, `-readonly`) are created or updated, THE Provisioner SHALL include `ssm:GetParameter` and `secretsmanager:GetSecretValue` permissions scoped to the project's parameter/secret path prefix (e.g., `arn:aws:ssm:*:*:parameter/myproject/*`) in the `-developer` role policy, and `secretsmanager:GetSecretValue` scoped to project secrets in the `-readonly` role policy where appropriate.

---

### NFR-11: Security Monitoring and Alerting

**Rationale**: The platform manages IAM roles and triggers infrastructure changes. Lightweight security monitoring detects misuse, misconfiguration, and potential security incidents early, without requiring a full SIEM for a POC context.

**Default alert thresholds (configurable in Config_Repo; all events dual-written to CloudWatch Logs and S3 audit bucket; alerts delivered via SNS to Platform_Admin):**

1. THE Platform SHALL generate a security alert for the following events:
   - **Failed authentication**: 5 or more consecutive IAM role assumption failures within 10 minutes for the same user identity. *Rationale: consistent with NIST 800-63 guidance; indicates credential stuffing or misconfigured tooling rather than a typo.*
   - **Rate limit breach**: any single rate limit breach by any user. *Rationale: legitimate internal users rarely hit rate limits; any breach is worth visibility on an internal tool.*
   - **Privilege escalation attempt**: any Developer submitting a request targeting `staging` or `prod` environments (already blocked by the portal, but the attempt is security-relevant and should be visible).
   - **Off-hours Terraform run**: any provisioning run triggered outside Monday–Friday 07:00–20:00 local time. *Rationale: not blocked — legitimate on-call deployments exist — but flagged for admin visibility.*
   - **Bulk request anomaly**: any single user submitting more than 20 resource requests within any 1-hour window, even within per-minute rate limits. *Rationale: indicates automation that should be reviewed regardless of whether individual rate limits are breached.*
   - **Out-of-band IAM policy change**: any modification to a project IAM role (`-deployer`, `-developer`, `-readonly`) detected outside of a platform-triggered Terraform run (detected via CloudTrail event monitoring). *Rationale: indicates a change bypassing the platform's governance controls.*
2. ALL security alert events SHALL be written as security audit events to the audit log (dual-write to CloudWatch Logs and S3 audit bucket).
3. Security alert thresholds SHALL be configurable in the Config_Repo without a code deployment.

---

### NFR-12: Resource Expiry Lifecycle Enforcement

**Rationale**: The `expiry_date` tag creates accountability for resource lifetime, but a tag alone is not enforced without automated lifecycle management. A graduated warning → gate → grace period → auto-deprovision model balances operational safety with governance discipline. Full auto-deprovision is not triggered until well after multiple human-visible warnings, reducing accidental data loss risk. All parameters are configurable to adapt to team risk tolerance.

**Configurable lifecycle parameters (stored in Config_Repo; defaults documented below with rationale):**

- `expiry_warning_days_first`: **14 days** before expiry. *Rationale: enough lead time to act without being so far in advance that warnings are ignored.*
- `expiry_warning_days_second`: **7 days** before expiry. *Rationale: a closer reminder for owners who missed the first warning.*
- `expiry_grace_period_days`: **30 days** after expiry date. *Rationale: generous grace period catches genuine oversights; Team Lead must actively choose to extend or decommission.*
- `expiry_final_warning_days_before_deprovision`: **7 days** before end of grace period (T+23). *Rationale: final escalation including Platform_Admin gives maximum visibility before destructive action.*
- `expiry_auto_deprovision_enabled`: **true**. *Rationale: enforcement without auto-deprovision degrades to a notify-only model; set to false to revert to manual decommission only.*
- `expiry_deprovision_requires_admin_approval`: **false**. *Rationale: requiring admin approval for every auto-deprovision adds operational overhead; set to true for high-risk environments.*

**Lifecycle flow:**

1. AT T-14 days (14 days before `expiry_date`), THE Platform SHALL send a warning email to the resource `owner` and the project's Team_Lead identifying the resource, its expiry date, and the action required (extend or decommission).
2. AT T-7 days (7 days before `expiry_date`), THE Platform SHALL send a second warning email to the resource `owner` and Team_Lead.
3. AT T-0 (`expiry_date`), THE Platform SHALL:
   a. Update the resource status to `expiry_pending` in the portal.
   b. Block new deployments to the resource (the `-deployer` role policy is not updated with new ARNs for this resource while in `expiry_pending` status).
   c. Notify the Team_Lead that immediate action is required: extend the expiry date (subject to the 90-day maximum from today) or approve decommission.
4. WHILE a resource is in `expiry_pending` status, THE Team_Lead SHALL be able to extend the `expiry_date` (subject to the 90-day cap from the date of extension) or initiate decommission via the portal.
5. AT T+23 days (7 days before end of grace period), IF no Team_Lead action has been taken, THE Platform SHALL send a final warning email to the resource `owner`, Team_Lead, AND Platform_Admin, escalating the pending expiry.
6. AT T+30 days (end of grace period), IF `expiry_auto_deprovision_enabled` is true AND no Team_Lead action has been taken, THE Platform SHALL:
   a. IF `expiry_deprovision_requires_admin_approval` is false: automatically trigger a Terraform Cloud deprovision run to destroy the resource.
   b. IF `expiry_deprovision_requires_admin_approval` is true: notify the Platform_Admin that manual approval is required to trigger deprovision.
7. WHEN an auto-deprovision run completes successfully, THE Platform SHALL:
   a. Update the resource status to `deprovisioned`.
   b. Remove the resource ARN from the project's `-deployer` role policy.
   c. Write a lifecycle audit event (dual-write to CloudWatch Logs and S3 audit bucket) recording the deprovisioned resource ARN, the triggering expiry date, and the UTC timestamp.
8. IF an auto-deprovision run fails, THE Platform SHALL update the resource status to `deprovision_failed`, alert the Platform_Admin, and write a failure audit event.
9. ALL expiry notification emails and status transitions SHALL be written as lifecycle audit events to the audit log.

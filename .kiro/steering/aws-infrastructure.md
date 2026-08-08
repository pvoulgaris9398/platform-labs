# AWS and Infrastructure Best Practices

## General AWS Principles
- Follow the AWS Well-Architected Framework pillars: Operational Excellence, Security, Reliability, Performance Efficiency, Cost Optimisation, Sustainability.
- Always use IAM roles — never use IAM users or long-lived access keys for application workloads.
- Apply least-privilege IAM policies. Start with deny-all and add only the permissions explicitly needed. Scope `Resource` to specific ARNs, not `"*"`, wherever possible.
- Tag every AWS resource with the standard tag set: `cost_center`, `environment`, `team`, `owner`, `project`, `application_name`, `expiry_date`, `created_by`. Resources without required tags must not be created by the platform.
- Enable CloudTrail in all regions. All IAM and infrastructure changes are logged.

## Terraform Conventions
- Use Terraform 1.6+ with the `required_providers` block pinned to exact provider versions.
- All resources are defined in modules under `terraform/modules/`. Root modules in `terraform/environments/` call modules — they do not define resources directly.
- Module interface: every module exposes a `variables.tf` with full descriptions and type constraints, and an `outputs.tf` for all values needed by callers.
- Use `terraform.tfvars` files per environment. Never commit `terraform.tfvars` containing sensitive values — use environment variables or Terraform Cloud variable sets.
- Remote state is stored in S3 with DynamoDB state locking. Never use local state in any environment beyond local development.
- Run `terraform fmt` and `terraform validate` in CI before every plan. Run `tflint` and `checkov` for security scanning.
- Prefer `for_each` over `count` for resources created from a collection. `count` makes resource addresses fragile when the list changes.
- Use `lifecycle { prevent_destroy = true }` on stateful resources (RDS, S3 audit bucket, IAM roles).

## Secrets and Configuration
- No secrets in Terraform state. Use `sensitive = true` on outputs that contain secrets. Use `nonsensitive()` only when the value has been confirmed safe to expose.
- Application secrets (DB passwords, API tokens) live in AWS Secrets Manager. Config values (endpoints, feature flags) live in SSM Parameter Store under `/platform/` prefix.
- ECS tasks receive secrets via `secrets` block in the task definition (reference to Secrets Manager ARN) — not as plaintext environment variables.
- Rotate secrets using Secrets Manager automatic rotation where a rotation Lambda is available.

## Networking
- All application workloads run in private VPC subnets. Only ALBs and NAT Gateways are in public subnets.
- Use VPC endpoints (Gateway for S3, Interface for SSM, Secrets Manager, CloudWatch Logs) to avoid routing AWS API calls over the public internet.
- Security groups follow the principle of least privilege: allow only the specific ports and source security groups needed. No `0.0.0.0/0` inbound rules except on the ALB for HTTPS (port 443).
- Enable VPC Flow Logs to CloudWatch for all VPCs. Retain flow logs for 30 days minimum.
- Use AWS-managed TLS certificates (ACM) on all ALBs. Do not manage certificates manually. Enforce TLS 1.2+ minimum; prefer TLS 1.3.

## ECS Fargate
- Task definitions pin the container image to a specific digest (`:sha256:...`) in production, not a mutable tag like `:latest`. Use mutable tags only in dev/uat.
- Set CPU and memory limits explicitly on every task definition. Right-size based on observed metrics — do not default to maximum values.
- Use ECS task roles (not execution roles) for application-level AWS API permissions. Execution roles are for ECR pull and secrets injection only.
- Enable ECS Exec for debugging in non-production environments. Disable in production.
- Use ECS Service Connect or AWS Cloud Map for internal service discovery. Do not hardcode private IP addresses.
- Configure health checks on the ECS service matching the `/health` endpoint. Set appropriate `unhealthyThreshold` and `gracePeriod` to avoid false restarts during startup.

## RDS PostgreSQL
- Enable Multi-AZ for all non-development RDS instances.
- Automated backups with a 7-day retention period minimum. Enable point-in-time recovery.
- Use RDS parameter groups (not the default group) so parameters are version-controlled and auditable.
- The application connects to RDS using an IAM-authenticated connection or a dedicated application user — never the master user.
- Enable RDS Enhanced Monitoring and Performance Insights. Set `slow_query_log` threshold to 1 second.
- Store RDS credentials in Secrets Manager with automatic rotation.

## S3
- Enable versioning on all buckets storing state or audit data.
- Block all public access (`BlockPublicAcls`, `BlockPublicPolicy`, `IgnorePublicAcls`, `RestrictPublicBuckets` all `true`) on all buckets unless explicitly serving public content.
- Enable default encryption (SSE-S3 or SSE-KMS) on all buckets.
- Use Object Lock (Governance mode) on the audit bucket with a 90-day retention period. Apply a lifecycle rule to transition to Glacier Instant Retrieval after 90 days.
- Enable S3 server access logging on all buckets — log to a dedicated `platform-access-logs` bucket.
- Use bucket policies to enforce `aws:SecureTransport` (HTTPS only). Deny all HTTP requests.

## CloudWatch and Observability
- Create Log Groups with explicit retention policies. Never use the default (never expire) — use 90 days for audit logs, 30 days for application logs, 7 days for debug logs.
- Use structured JSON logging in all applications. Filter pattern `{ $.level = "ERROR" }` for error alarms.
- Create CloudWatch Alarms for: ECS task CPU > 80%, ECS task memory > 80%, RDS connections > 80% max, ALB 5xx error rate > 1%, provisioning stuck runs (custom metric).
- Use CloudWatch Dashboards to surface: active request counts by status, provisioning success/failure rate, audit event volume, cost anomaly alerts.

## Cost
- Use AWS Cost Anomaly Detection on all cost centers and projects (provisioned at project registration time).
- Set AWS Budgets alerts at 80% and 100% of the monthly budget for each project.
- Use S3 Intelligent-Tiering or explicit lifecycle rules on all S3 buckets storing time-series or archival data.
- Tag-based cost allocation reports in AWS Cost Explorer are the primary cost reporting mechanism — consistent tagging is non-negotiable.
- Right-size ECS tasks and RDS instances based on CloudWatch metrics, not assumptions. Review every 30 days in the POC phase.

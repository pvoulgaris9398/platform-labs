# AWS Developer Platform exercise runbook

This walkthrough runs the portal locally and optionally uses MiniStack as an AWS-compatible emulator.
It does not contact an AWS account or apply the production Terraform environment.

## Prerequisites

- Docker Desktop with Linux containers enabled
- Git for Windows with Git Bash
- `curl` and `jq` available in Git Bash
- AWS CLI v2 for the MiniStack checks
- Node.js 22+ with npm/npx for the browser UI; a global pnpm installation is optional
- Python 3.12+ only if running the API outside Docker

Run commands from this `aws-developer-platform` directory.

### Running pnpm from Git Bash on Windows

Altnatively, install onto windows via instructions [here](https://pnpm.io/installation)

```bash
curl -fsSL https://get.pnpm.io/install.sh | sh -
```

The pnpm project recommends npm or Corepack on Windows. This runbook uses `npx` so no global pnpm
installation is required. Define this helper once in each Git Bash terminal that runs frontend
commands:

```bash
pnpmw() { npx --yes pnpm@latest-11 "$@"; }
```

`latest-11` selects the current stable pnpm 11 release; `--yes` suppresses the first-run npx prompt.
You can also run a single command without the helper, for example
`npx --yes pnpm@latest-11 install`.

## 1. Start the local stack

Start PostgreSQL, the FastAPI service, and the opt-in MiniStack profile:

```bash
docker compose --profile ministack up --build -d
docker compose ps
```

Install `jq` into Git Bash on Windows via an elevanted shell

```bash
curl -L -o /usr/bin/jq.exe https://github.com/jqlang/jq/releases/latest/download/jq-win64.exe
```

Wait for both health endpoints:

```bash
curl --fail --silent --show-error http://localhost:8000/health | jq .
curl --fail --silent --show-error http://localhost:4566/_ministack/health | jq .
```

Expected portal response: `status = ok`. MiniStack should return HTTP 200 and service status data.

If startup fails, inspect logs:

```bash
docker compose logs api db ministack --tail 100
```

## 2. MiniStack configuration block

The Compose service uses the following configuration. It persists service metadata, S3 bytes, and
RDS data between restarts and gives nested Lambda/RDS containers access to Docker.

```yaml
ministack:
  image: ministackorg/ministack:latest
  profiles: ["ministack"]
  ports:
    - "4566:4566"
  environment:
    GATEWAY_PORT: "4566"
    LOG_LEVEL: INFO
    MINISTACK_REGION: us-east-1
    PERSIST_STATE: "1"
    STATE_DIR: /tmp/ministack-state
    S3_PERSIST: "1"
    S3_DATA_DIR: /tmp/ministack-data/s3
    RDS_PERSIST: "1"
    LAMBDA_EXECUTOR: docker
    DOCKER_NETWORK: aws-developer-platform_default
  volumes:
    - ministack-state:/tmp/ministack-state
    - ministack-s3:/tmp/ministack-data/s3
    - //var/run/docker.sock:/var/run/docker.sock
```

For AWS CLI calls in this shell, use dummy credentials and the shared endpoint:

```bash
export AWS_ACCESS_KEY_ID="test"
export AWS_SECRET_ACCESS_KEY="test"
export AWS_DEFAULT_REGION="us-east-1"
export MINISTACK_ENDPOINT="http://localhost:4566"
```

For a Terraform exercise, add this provider block to a disposable root module. Do not add it to the
real AWS `dev` root or reuse a production state file.

```hcl
provider "aws" {
  region                      = "us-east-1"
  access_key                  = "test"
  secret_key                  = "test"
  s3_use_path_style           = true
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true

  endpoints {
    s3             = "http://localhost:4566"
    dynamodb       = "http://localhost:4566"
    lambda         = "http://localhost:4566"
    iam            = "http://localhost:4566"
    ec2            = "http://localhost:4566"
    ecs            = "http://localhost:4566"
    cloudwatch     = "http://localhost:4566"
    secretsmanager = "http://localhost:4566"
    ssm            = "http://localhost:4566"
    rds            = "http://localhost:4566"
    sns            = "http://localhost:4566"
    sts            = "http://localhost:4566"
  }
}
```

## 3. Establish a development session

The local session endpoint deliberately works only when `ENVIRONMENT=development`. Keep the cookie
jar for subsequent calls:

```bash
export API="http://localhost:8000/api/v1"
export COOKIE_JAR="$(pwd)/.walkthrough-cookies.txt"

curl --fail --silent --show-error \
  --cookie-jar "$COOKIE_JAR" \
  --header 'Content-Type: application/json' \
  --data '{
    "principal_arn": "arn:aws:sts::000000000000:assumed-role/platform-team-lead/walkthrough",
    "platform_role": "Team_Lead",
    "role_tags": {
      "display_name": "Walkthrough Team Lead",
      "email": "lead@example.test",
      "team": "platform"
    }
  }' \
  "$API/auth/session" | jq .
```

## 4. Register a project

```bash
PROJECT_RESPONSE="$(curl --fail --silent --show-error \
  --cookie "$COOKIE_JAR" \
  --header 'Content-Type: application/json' \
  --data '{
    "name": "walkthrough",
    "description": "Local MiniStack exercise",
    "application_name": "developer-portal-lab",
    "team_name": "platform",
    "cost_center": "engineering",
    "allowed_environments": ["dev", "uat"],
    "allowed_resource_types": ["s3", "lambda", "dynamodb"],
    "monthly_budget_usd": 100,
    "tags": {"purpose": "walkthrough"}
  }' \
  "$API/projects")"
export PROJECT_ID="$(jq -r '.data.id' <<<"$PROJECT_RESPONSE")"
jq . <<<"$PROJECT_RESPONSE"
printf 'Project ID: %s\n' "$PROJECT_ID"
```

In local development, project registration uses `PROJECT_IAM_BACKEND=ministack` and sends the
project IAM scaffolding calls to `MINISTACK_ENDPOINT`. A successful response includes
`deployer_role_arn`, `developer_role_arn`, and `readonly_role_arn` values for the three local POC
roles. If MiniStack is not running or rejects the IAM calls, the project is still saved with
`status: "iam_failed"` and `iam_error_details` explains what failed.

Re-running this step with persisted PostgreSQL state will conflict with the unique project name. Use
a new name or reset the local database volume as described under cleanup.

## 5. Submit a request that triggers guardrails

The deliberately weak S3 configuration exercises validation, cost estimation, and soft warnings:

```bash
export EXPIRY_DATE="$(date -d '+30 days' +%F)"
REQUEST_BODY="$(jq --null-input \
  --arg project_id "$PROJECT_ID" \
  --arg expiry_date "$EXPIRY_DATE" \
  '{
    project_id: $project_id,
    resource_type: "s3",
    name_suffix: "artifacts",
    region: "us-east-1",
    environment: "dev",
    expiry_date: $expiry_date,
    tags: {owner: "lead@example.test"},
    resource_config: {
      storage_gb: 25,
      block_public_access: false,
      encryption: false,
      versioning: false,
      secure_transport: false,
      access_logging: false
    }
  }')"
REQUEST_RESPONSE="$(curl --fail --silent --show-error \
  --cookie "$COOKIE_JAR" \
  --header 'Content-Type: application/json' \
  --data "$REQUEST_BODY" \
  "$API/requests")"
export REQUEST_ID="$(jq -r '.data.id' <<<"$REQUEST_RESPONSE")"
jq '.data' <<<"$REQUEST_RESPONSE"
jq '.data.guardrail_warnings[] | {rule_id, rule_name, message}' <<<"$REQUEST_RESPONSE"
```

Expected status: `guardrail_review`, with warnings `S3-G1` through `S3-G5`.

## 6. Acknowledge guardrails and approve

```bash
curl --fail --silent --show-error --request POST \
  --cookie "$COOKIE_JAR" "$API/requests/$REQUEST_ID/acknowledge" | jq .

curl --fail --silent --show-error --request POST \
  --cookie "$COOKIE_JAR" "$API/approvals/$REQUEST_ID/approve" | jq .
```

The request should now be `provisioned` and include `provisioned_arn`. In local development, the
approval endpoint provisions S3 requests through MiniStack rather than Terraform Cloud.

## 7. Upload a test object to the provisioned S3 bucket

The provisioned bucket name is the request's `resource_name`. You can capture it from the request
response or the dashboard:

```bash
export BUCKET_NAME="$(curl --fail --silent --show-error \
  --cookie "$COOKIE_JAR" "$API/requests/$REQUEST_ID" | jq -r '.data.resource_name')"
printf 'hello from MiniStack\n' > sample.txt
aws --endpoint-url="$MINISTACK_ENDPOINT" s3 cp sample.txt \
  "s3://$BUCKET_NAME/sample.txt" \
  --checksum-algorithm SHA256
aws --endpoint-url="$MINISTACK_ENDPOINT" s3 ls "s3://$BUCKET_NAME/"
```

The `--checksum-algorithm SHA256` flag avoids newer AWS CLI defaults such as `CRC64NVME`, which this
MiniStack image does not bundle optional native support for.

Open the uploaded object through the MiniStack AWS proxy URL:

```text
http://localhost:4566/<bucket-name>/sample.txt
```

For example:

```text
http://localhost:4566/platform-walkthrough-dev-artifacts/sample.txt
```

## 8. Exercise cost estimation directly

```bash
curl --fail --silent --show-error \
  --header 'Content-Type: application/json' \
  --data '{
    "resource_type": "lambda",
    "resource_config": {
      "memory_mb": 512,
      "duration_seconds": 1,
      "monthly_invocations": 1000000
    }
  }' \
  "$API/cost/estimate" | jq .
```

The response includes `stale = true` because local fallback rates are used.

## 9. Exercise MiniStack services

Create and inspect representative resources through the AWS CLI:

```bash
aws --endpoint-url="$MINISTACK_ENDPOINT" s3 mb s3://platform-walkthrough-dev-artifacts
printf 'hello from MiniStack\n' > ministack-object.txt
aws --endpoint-url="$MINISTACK_ENDPOINT" s3 cp ministack-object.txt \
  s3://platform-walkthrough-dev-artifacts/ministack-object.txt \
  --checksum-algorithm SHA256
aws --endpoint-url="$MINISTACK_ENDPOINT" s3 ls s3://platform-walkthrough-dev-artifacts

aws --endpoint-url="$MINISTACK_ENDPOINT" dynamodb create-table \
  --table-name platform.walkthrough.dev.Sessions \
  --attribute-definitions AttributeName=id,AttributeType=S \
  --key-schema AttributeName=id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST
aws --endpoint-url="$MINISTACK_ENDPOINT" dynamodb describe-table \
  --table-name platform.walkthrough.dev.Sessions
```

MiniStack accepts dummy credentials. It stores IAM resources but does not enforce their policies, so
use the portal's RBAC and pure IAM-policy tests to exercise authorization logic.

## 10. Run the browser UI

In a separate terminal:

```bash
cd frontend
pnpmw install
pnpmw dev
```

Open `http://localhost:5173`. Vite proxies `/api` to the API on port 8000. If the browser has no
session cookie, it redirects to `/login`. Select **Team lead** and choose **Sign in**, then open the
project catalogue. The local sign-in endpoint refuses to operate outside development mode; a
deployed environment must replace it with the configured STS verification flow.

## 11. Run automated verification

Backend:

```bash
./.venv/Scripts/python.exe -m ruff check .
./.venv/Scripts/python.exe -m ruff format --check .
./.venv/Scripts/python.exe -m pytest -q
```

Frontend:

```bash
cd frontend
pnpmw run build
pnpmw test
cd ..
```

Production Terraform syntax validation without contacting AWS:

```bash
terraform fmt -check -recursive terraform
terraform -chdir=terraform/environments/dev init -backend=false
terraform -chdir=terraform/environments/dev validate
```

Do not run `terraform apply` from `terraform/environments/dev` for this walkthrough.

## 11. Cleanup and reset

Stop containers while retaining data:

```bash
docker compose --profile ministack down
```

Reset all local PostgreSQL and MiniStack state. This is destructive to walkthrough-only container
data:

```bash
docker compose --profile ministack down --volumes
rm -f ministack-object.txt .walkthrough-cookies.txt
```

MiniStack does not automatically trigger EventBridge schedules. Exercise lifecycle calculations via
`POST /api/v1/lifecycle/run` or the automated property tests.

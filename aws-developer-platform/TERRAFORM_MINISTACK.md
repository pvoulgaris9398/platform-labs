# Terraform with MiniStack

This guide provisions disposable S3 and DynamoDB resources against the local MiniStack emulator
using Terraform. It does not contact an AWS account or apply the production Terraform environment.

> [!WARNING]
> Run `terraform apply` only from the disposable `terraform/ministack-lab` directory created below.
> Do not apply the configuration in `terraform/environments/dev`; that root represents real AWS
> infrastructure.

## Prerequisites

Install and configure the following before starting:

- Docker Desktop, running with Linux containers enabled
- Git for Windows and Git Bash
- Terraform `>= 1.6.0, < 2.0.0`
- AWS CLI v2
- `curl` and `jq` available in Git Bash
- Internet access for the initial Terraform provider download

Verify the required commands from Git Bash:

```bash
docker --version
docker compose version
terraform version
aws --version
curl --version
jq --version
```

Run all remaining commands from Git Bash unless a step says otherwise.

## 1. Open the project directory

```bash
cd /c/Users/Peter/_work/_code/platform-labs/aws-developer-platform
```

## 2. Start and verify the local stack

Start PostgreSQL, the API, and the opt-in MiniStack service:

```bash
docker compose --profile ministack up --build -d
docker compose --profile ministack ps
```

Wait until MiniStack reports healthy, then check its endpoint:

```bash
curl --fail --silent --show-error \
  http://localhost:4566/_ministack/health | jq .
```

The response should include service statuses such as `"s3": "available"` and
`"dynamodb": "available"`. If startup fails, inspect the logs:

```bash
docker compose logs ministack --tail 100
```

## 3. Configure dummy AWS credentials

MiniStack does not need real AWS credentials, but AWS clients require credential values to be
present. Set disposable values in the current Git Bash session:

```bash
export AWS_ACCESS_KEY_ID="test"
export AWS_SECRET_ACCESS_KEY="test"
export AWS_DEFAULT_REGION="us-east-1"
export AWS_REGION="us-east-1"
export MINISTACK_ENDPOINT="http://localhost:4566"
```

Confirm that the AWS CLI can reach the emulator:

```bash
aws --endpoint-url="$MINISTACK_ENDPOINT" sts get-caller-identity
```

A simulated identity response means the endpoint is reachable. These values apply only to the
current shell and must be exported again in a new terminal.

## 4. Create a disposable Terraform root

Create and enter a directory with independent local Terraform state:

```bash
mkdir -p terraform/ministack-lab
cd terraform/ministack-lab
```

Do not configure an S3 backend in this directory. Terraform will keep this exercise's state locally.

### Create `versions.tf`

```bash
cat > versions.tf <<'EOF'
terraform {
  required_version = ">= 1.6.0, < 2.0.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.10.0"
    }
  }
}
EOF
```

This pins the AWS provider to the version used by the repository's development environment.

### Create `main.tf`

```bash
cat > main.tf <<'EOF'
provider "aws" {
  region     = "us-east-1"
  access_key = "test"
  secret_key = "test"

  s3_use_path_style           = true
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true
  skip_region_validation      = true

  endpoints {
    dynamodb = "http://localhost:4566"
    s3       = "http://localhost:4566"
    sts      = "http://localhost:4566"
  }
}

resource "aws_s3_bucket" "artifacts" {
  bucket = "platform-terraform-lab-dev-artifacts"

  tags = {
    Environment = "dev"
    ManagedBy   = "terraform"
    Project     = "ministack-lab"
  }
}

resource "aws_s3_bucket_versioning" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_dynamodb_table" "sessions" {
  name         = "platform.terraform-lab.dev.Sessions"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }

  tags = {
    Environment = "dev"
    ManagedBy   = "terraform"
    Project     = "ministack-lab"
  }
}
EOF
```

### Create `outputs.tf`

```bash
cat > outputs.tf <<'EOF'
output "bucket_name" {
  value = aws_s3_bucket.artifacts.bucket
}

output "dynamodb_table_name" {
  value = aws_dynamodb_table.sessions.name
}
EOF
```

The disposable root should now contain:

```text
terraform/ministack-lab/
|-- main.tf
|-- outputs.tf
`-- versions.tf
```

## 5. Format, initialize, and validate Terraform

```bash
terraform fmt
terraform init
terraform validate
```

Initialization downloads AWS provider `6.10.0` and creates `.terraform/` and
`.terraform.lock.hcl`. It does not create AWS or MiniStack resources. Validation should finish with:

```text
Success! The configuration is valid.
```

## 6. Review a saved plan

```bash
terraform plan -out=ministack.tfplan
```

Review the proposed S3 bucket, versioning configuration, public-access block, and DynamoDB table.
Make sure the plan does not contain production resource names or a remote state backend.

## 7. Apply the saved plan to MiniStack

```bash
terraform apply ministack.tfplan
```

Because this applies the saved plan, Terraform should not prompt for confirmation. The result should
include these outputs:

```text
bucket_name = "platform-terraform-lab-dev-artifacts"
dynamodb_table_name = "platform.terraform-lab.dev.Sessions"
```

## 8. Inspect the Terraform state

```bash
terraform state list
terraform output
```

The state list should contain:

```text
aws_dynamodb_table.sessions
aws_s3_bucket.artifacts
aws_s3_bucket_public_access_block.artifacts
aws_s3_bucket_versioning.artifacts
```

## 9. Verify resources through the AWS CLI

The environment variables from step 3 must still be present in this shell.

List the S3 buckets:

```bash
aws --endpoint-url="$MINISTACK_ENDPOINT" s3 ls
```

Inspect bucket versioning:

```bash
aws --endpoint-url="$MINISTACK_ENDPOINT" \
  s3api get-bucket-versioning \
  --bucket platform-terraform-lab-dev-artifacts
```

Inspect the DynamoDB table:

```bash
aws --endpoint-url="$MINISTACK_ENDPOINT" \
  dynamodb describe-table \
  --table-name platform.terraform-lab.dev.Sessions | \
  jq '.Table | {TableName, TableStatus, BillingModeSummary}'
```

## 10. Confirm idempotency

Run another plan without changing the configuration:

```bash
terraform plan
```

Expected result:

```text
No changes. Your infrastructure matches the configuration.
```

## 11. Destroy the exercise resources

Remain in `terraform/ministack-lab` and review a saved destroy plan:

```bash
terraform plan -destroy -out=destroy.tfplan
terraform apply destroy.tfplan
```

Confirm that the resources are gone:

```bash
aws --endpoint-url="$MINISTACK_ENDPOINT" s3 ls
aws --endpoint-url="$MINISTACK_ENDPOINT" dynamodb list-tables | jq .
```

## 12. Remove the disposable Terraform files

Only do this after `terraform apply destroy.tfplan` succeeds:

```bash
cd ../..
rm -rf terraform/ministack-lab
```

This removes only the disposable configuration, downloaded provider, saved plans, and local state.

## 13. Stop or reset the local stack

Stop the containers while retaining PostgreSQL and MiniStack data:

```bash
docker compose --profile ministack down
```

To delete all walkthrough-only Docker volume data as well:

```bash
docker compose --profile ministack down --volumes
```

The `--volumes` form is destructive to local PostgreSQL and MiniStack data.

## Troubleshooting

### Cannot connect to port 4566

Confirm that the profile was included and inspect its logs:

```bash
docker compose --profile ministack up -d ministack
docker compose --profile ministack ps
docker compose logs ministack --tail 100
```

### Terraform tries to use real AWS

Stop before applying. Confirm that the provider contains the MiniStack `endpoints` block and that the
current directory is `terraform/ministack-lab`:

```bash
pwd
grep -A5 'endpoints {' main.tf
```

### AWS CLI cannot find credentials

Repeat the exports from step 3 in the current shell.

### Terraform reports that resources already exist

MiniStack persists data in Docker volumes. Either choose new resource names, import the existing
resources into this exercise's state, or reset the walkthrough volumes after confirming that their
data is no longer needed.

## Emulator limitations

MiniStack is suitable for this local exercise, but it does not reproduce every AWS validation, IAM
enforcement rule, or service behavior. Successful local provisioning is not a substitute for
production Terraform validation, security review, or an approved plan against the intended AWS
environment.

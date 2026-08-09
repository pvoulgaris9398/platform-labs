"""Local resource provisioning adapters for the MiniStack POC backend."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from io import BytesIO
from typing import Protocol
from urllib.parse import urlencode
from zipfile import ZIP_DEFLATED, ZipFile

import httpx

from app.config import get_settings
from app.db.models import ResourceRequest


@dataclass(frozen=True)
class LocalProvisioningResult:
    """Result of a local MiniStack provisioning operation."""

    resource_arn: str


class LocalResourceProvisioner(Protocol):
    """Provision an approved resource request in the local POC backend."""

    async def provision(self, request: ResourceRequest) -> LocalProvisioningResult:
        """Provision the requested resource and return its ARN."""


class LocalProvisioningError(RuntimeError):
    """Raised when local resource provisioning cannot be completed."""


class MiniStackResourceProvisioner:
    """Provision supported resources through MiniStack's AWS-compatible endpoint."""

    def __init__(
        self,
        endpoint: str,
        region: str,
        account_id: str,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.region = region
        self.account_id = account_id
        self.client = client or httpx.AsyncClient(timeout=10)

    async def provision(self, request: ResourceRequest) -> LocalProvisioningResult:
        """Provision the resource represented by an approved request."""

        if request.resource_type == "s3":
            return await self._create_s3_bucket(request)
        if request.resource_type == "lambda":
            return await self._create_lambda_function(request)
        if request.resource_type == "dynamodb":
            return await self._create_dynamodb_table(request)
        if request.resource_type == "aurora":
            return await self._create_aurora_cluster(request)
        if request.resource_type == "rds_postgresql":
            return await self._create_rds_postgresql_instance(request)
        raise LocalProvisioningError(
            f"MiniStack local provisioning does not support {request.resource_type} yet"
        )

    async def _create_s3_bucket(self, request: ResourceRequest) -> LocalProvisioningResult:
        bucket_url = f"{self.endpoint}/{request.resource_name}"
        response = await self.client.put(bucket_url, headers=self._aws_headers("s3"))
        if response.status_code >= 400 and "BucketAlreadyOwnedByYou" not in response.text:
            raise LocalProvisioningError(f"MiniStack S3 bucket create failed: {response.text}")
        return LocalProvisioningResult(resource_arn=f"arn:aws:s3:::{request.resource_name}")

    async def _create_lambda_function(self, request: ResourceRequest) -> LocalProvisioningResult:
        runtime = str(request.resource_config.get("runtime", "python3.12"))
        handler = str(request.resource_config.get("handler", "index.handler"))
        memory_size = int(request.resource_config.get("memory_mb", 128))
        timeout = int(request.resource_config.get("timeout_seconds", 3))
        payload = {
            "FunctionName": request.resource_name,
            "Runtime": runtime,
            "Role": f"arn:aws:iam::{self.account_id}:role/{request.resource_name}-local-lambda",
            "Handler": handler,
            "Code": {"ZipFile": self._default_lambda_zip()},
            "Description": "Local MiniStack POC Lambda function",
            "MemorySize": memory_size,
            "Timeout": timeout,
            "Tags": {key: str(value) for key, value in request.tags.items()},
        }
        response = await self.client.post(
            f"{self.endpoint}/2015-03-31/functions",
            json=payload,
            headers=self._aws_headers("lambda"),
        )
        if response.status_code >= 400 and "ResourceConflictException" not in response.text:
            raise LocalProvisioningError(f"MiniStack Lambda create failed: {response.text}")
        return LocalProvisioningResult(
            resource_arn=(
                f"arn:aws:lambda:{request.region}:{self.account_id}:function:{request.resource_name}"
            )
        )

    async def _create_dynamodb_table(self, request: ResourceRequest) -> LocalProvisioningResult:
        key_name = str(request.resource_config.get("partition_key", "id"))
        payload = {
            "TableName": request.resource_name,
            "AttributeDefinitions": [{"AttributeName": key_name, "AttributeType": "S"}],
            "KeySchema": [{"AttributeName": key_name, "KeyType": "HASH"}],
            "BillingMode": str(request.resource_config.get("billing_mode", "PAY_PER_REQUEST")),
            "Tags": [{"Key": key, "Value": str(value)} for key, value in request.tags.items()],
        }
        response = await self.client.post(
            self.endpoint,
            json=payload,
            headers=self._aws_headers("dynamodb")
            | {"X-Amz-Target": "DynamoDB_20120810.CreateTable"},
        )
        if response.status_code >= 400 and "ResourceInUseException" not in response.text:
            raise LocalProvisioningError(f"MiniStack DynamoDB create failed: {response.text}")
        return LocalProvisioningResult(
            resource_arn=f"arn:aws:dynamodb:{request.region}:{self.account_id}:table/{request.resource_name}"
        )

    async def _create_aurora_cluster(self, request: ResourceRequest) -> LocalProvisioningResult:
        params = {
            "Action": "CreateDBCluster",
            "Version": "2014-10-31",
            "DBClusterIdentifier": request.resource_name,
            "Engine": str(request.resource_config.get("engine", "aurora-postgresql")),
            "DatabaseName": str(request.resource_config.get("database_name", "appdb")),
            "MasterUsername": str(request.resource_config.get("master_username", "platform_admin")),
            "MasterUserPassword": str(
                request.resource_config.get("master_password", "local-development-only")
            ),
        }
        response = await self.client.post(
            self.endpoint,
            content=urlencode(params),
            headers=self._aws_headers("rds")
            | {"Content-Type": "application/x-www-form-urlencoded"},
        )
        if response.status_code >= 400 and "DBClusterAlreadyExistsFault" not in response.text:
            raise LocalProvisioningError(f"MiniStack Aurora create failed: {response.text}")
        return LocalProvisioningResult(
            resource_arn=f"arn:aws:rds:{request.region}:{self.account_id}:cluster:{request.resource_name}"
        )

    async def _create_rds_postgresql_instance(
        self, request: ResourceRequest
    ) -> LocalProvisioningResult:
        params = {
            "Action": "CreateDBInstance",
            "Version": "2014-10-31",
            "DBInstanceIdentifier": request.resource_name,
            "Engine": "postgres",
            "DBInstanceClass": str(
                request.resource_config.get("db_instance_class", "db.t4g.micro")
            ),
            "AllocatedStorage": str(request.resource_config.get("allocated_storage_gb", 20)),
            "DBName": str(request.resource_config.get("database_name", "appdb")),
            "MasterUsername": str(request.resource_config.get("master_username", "platform_admin")),
            "MasterUserPassword": str(
                request.resource_config.get("master_password", "local-development-only")
            ),
        }
        response = await self.client.post(
            self.endpoint,
            content=urlencode(params),
            headers=self._aws_headers("rds")
            | {"Content-Type": "application/x-www-form-urlencoded"},
        )
        if response.status_code >= 400 and "DBInstanceAlreadyExists" not in response.text:
            raise LocalProvisioningError(f"MiniStack RDS PostgreSQL create failed: {response.text}")
        return LocalProvisioningResult(
            resource_arn=f"arn:aws:rds:{request.region}:{self.account_id}:db:{request.resource_name}"
        )

    @staticmethod
    def _default_lambda_zip() -> str:
        buffer = BytesIO()
        with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
            archive.writestr(
                "index.py",
                "def handler(event, context):\n    return {'statusCode': 200, 'body': 'ok'}\n",
            )
        return base64.b64encode(buffer.getvalue()).decode()

    def _aws_headers(self, service: str) -> dict[str, str]:
        return {
            "Authorization": (
                "AWS4-HMAC-SHA256 Credential=test/20200101/"
                f"{self.region}/{service}/aws4_request, SignedHeaders=host, Signature=test"
            ),
            "X-Amz-Date": "20200101T000000Z",
        }


def get_local_resource_provisioner() -> LocalResourceProvisioner:
    """Return the configured local resource provisioner."""

    settings = get_settings()
    return MiniStackResourceProvisioner(
        endpoint=settings.ministack_endpoint,
        region=settings.aws_region,
        account_id=settings.ministack_account_id,
    )

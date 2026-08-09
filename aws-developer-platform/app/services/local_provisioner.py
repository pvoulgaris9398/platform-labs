"""Local resource provisioning adapters for the MiniStack POC backend."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

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

        if request.resource_type != "s3":
            raise LocalProvisioningError(
                f"MiniStack local provisioning does not support {request.resource_type} yet"
            )
        return await self._create_s3_bucket(request)

    async def _create_s3_bucket(self, request: ResourceRequest) -> LocalProvisioningResult:
        bucket_url = f"{self.endpoint}/{request.resource_name}"
        response = await self.client.put(bucket_url, headers=self._aws_headers("s3"))
        if response.status_code >= 400 and "BucketAlreadyOwnedByYou" not in response.text:
            raise LocalProvisioningError(f"MiniStack S3 bucket create failed: {response.text}")
        return LocalProvisioningResult(resource_arn=f"arn:aws:s3:::{request.resource_name}")

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

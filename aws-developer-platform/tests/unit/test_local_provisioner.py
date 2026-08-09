"""Local MiniStack provisioning tests."""

import httpx
import pytest

from app.db.models import ResourceRequest
from app.services.local_provisioner import MiniStackResourceProvisioner


@pytest.mark.asyncio
async def test_ministack_resource_provisioner_creates_s3_bucket() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, text="")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provisioner = MiniStackResourceProvisioner(
        "http://ministack.test:4566",
        region="us-east-1",
        account_id="000000000000",
        client=client,
    )
    request = ResourceRequest(
        project_id="00000000-0000-0000-0000-000000000001",
        resource_type="s3",
        resource_name="platform-alpha-dev-artifacts",
        region="us-east-1",
        environment="dev",
        tags={},
        submitted_by="tester",
        expiry_date="2026-09-08",
    )

    result = await provisioner.provision(request)

    assert result.resource_arn == "arn:aws:s3:::platform-alpha-dev-artifacts"
    assert requests[0].method == "PUT"
    assert str(requests[0].url) == "http://ministack.test:4566/platform-alpha-dev-artifacts"

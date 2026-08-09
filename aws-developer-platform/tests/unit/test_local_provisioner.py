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


@pytest.mark.asyncio
async def test_ministack_resource_provisioner_creates_lambda_function() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(201, json={"FunctionArn": "ignored"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provisioner = MiniStackResourceProvisioner(
        "http://ministack.test:4566",
        region="us-east-1",
        account_id="000000000000",
        client=client,
    )
    request = ResourceRequest(
        project_id="00000000-0000-0000-0000-000000000001",
        resource_type="lambda",
        resource_name="platform-alpha-dev-worker",
        region="us-east-1",
        environment="dev",
        resource_config={"runtime": "python3.12", "memory_mb": 256, "timeout_seconds": 10},
        tags={},
        submitted_by="tester",
        expiry_date="2026-09-08",
    )

    result = await provisioner.provision(request)

    assert (
        result.resource_arn
        == "arn:aws:lambda:us-east-1:000000000000:function:platform-alpha-dev-worker"
    )
    assert requests[0].method == "POST"
    assert str(requests[0].url) == "http://ministack.test:4566/2015-03-31/functions"


@pytest.mark.asyncio
async def test_ministack_resource_provisioner_creates_dynamodb_table() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provisioner = MiniStackResourceProvisioner(
        "http://ministack.test:4566",
        region="us-east-1",
        account_id="000000000000",
        client=client,
    )
    request = ResourceRequest(
        project_id="00000000-0000-0000-0000-000000000001",
        resource_type="dynamodb",
        resource_name="platform.alpha.dev.Sessions",
        region="us-east-1",
        environment="dev",
        resource_config={"partition_key": "session_id"},
        tags={},
        submitted_by="tester",
        expiry_date="2026-09-08",
    )

    result = await provisioner.provision(request)

    assert (
        result.resource_arn
        == "arn:aws:dynamodb:us-east-1:000000000000:table/platform.alpha.dev.Sessions"
    )
    assert requests[0].headers["x-amz-target"] == "DynamoDB_20120810.CreateTable"


@pytest.mark.asyncio
async def test_ministack_resource_provisioner_creates_aurora_cluster() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, text="<CreateDBClusterResponse />")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provisioner = MiniStackResourceProvisioner(
        "http://ministack.test:4566",
        region="us-east-1",
        account_id="000000000000",
        client=client,
    )
    request = ResourceRequest(
        project_id="00000000-0000-0000-0000-000000000001",
        resource_type="aurora",
        resource_name="platform-alpha-dev-db",
        region="us-east-1",
        environment="dev",
        resource_config={"engine": "aurora-postgresql"},
        tags={},
        submitted_by="tester",
        expiry_date="2026-09-08",
    )

    result = await provisioner.provision(request)

    assert result.resource_arn == "arn:aws:rds:us-east-1:000000000000:cluster:platform-alpha-dev-db"
    assert "Action=CreateDBCluster" in requests[0].content.decode()


@pytest.mark.asyncio
async def test_ministack_resource_provisioner_creates_rds_postgresql_instance() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, text="<CreateDBInstanceResponse />")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provisioner = MiniStackResourceProvisioner(
        "http://ministack.test:4566",
        region="us-east-1",
        account_id="000000000000",
        client=client,
    )
    request = ResourceRequest(
        project_id="00000000-0000-0000-0000-000000000001",
        resource_type="rds_postgresql",
        resource_name="platform-alpha-dev-postgres",
        region="us-east-1",
        environment="dev",
        resource_config={"db_instance_class": "db.t4g.micro"},
        tags={},
        submitted_by="tester",
        expiry_date="2026-09-08",
    )

    result = await provisioner.provision(request)

    assert (
        result.resource_arn == "arn:aws:rds:us-east-1:000000000000:db:platform-alpha-dev-postgres"
    )
    body = requests[0].content.decode()
    assert "Action=CreateDBInstance" in body
    assert "Engine=postgres" in body

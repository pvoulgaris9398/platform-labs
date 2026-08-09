"""Project IAM scaffolding tests."""

from urllib.parse import parse_qs

import httpx
import pytest

from app.db.models import Project
from app.services.project_iam import MiniStackProjectIamScaffolder


@pytest.mark.asyncio
async def test_ministack_scaffolder_creates_project_roles_and_policies() -> None:
    seen_actions: list[tuple[str, str]] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        params = parse_qs(request.content.decode())
        action = params["Action"][0]
        role_name = params["RoleName"][0]
        seen_actions.append((action, role_name))
        if action == "CreateRole":
            body = f"""
            <CreateRoleResponse xmlns="https://iam.amazonaws.com/doc/2010-05-08/">
              <CreateRoleResult>
                <Role>
                  <Arn>arn:aws:iam::000000000000:role/{role_name}</Arn>
                </Role>
              </CreateRoleResult>
            </CreateRoleResponse>
            """
            return httpx.Response(200, text=body)
        return httpx.Response(200, text="<PutRolePolicyResponse />")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    scaffolder = MiniStackProjectIamScaffolder(
        "http://ministack.test:4566",
        region="us-east-1",
        account_id="000000000000",
        client=client,
    )
    project = Project(
        name="alpha",
        application_name="portal",
        team_name="platform",
        cost_center="engineering",
        default_owner="owner",
        registered_by="owner",
    )

    roles = await scaffolder.scaffold(project)

    assert roles.deployer_role_arn == "arn:aws:iam::000000000000:role/alpha-deployer"
    assert ("CreateRole", "alpha-deployer") in seen_actions
    assert ("PutRolePolicy", "alpha-readonly") in seen_actions

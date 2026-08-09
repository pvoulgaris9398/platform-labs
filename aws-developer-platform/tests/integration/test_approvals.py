"""Approval flow integration tests."""

import uuid
from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.main import app
from app.services.local_provisioner import LocalProvisioningResult, get_local_resource_provisioner
from app.services.project_iam import ProjectIamRoles, get_project_iam_scaffolder


class FakeProjectIamScaffolder:
    async def scaffold(self, project):
        return ProjectIamRoles(
            deployer_role_arn=f"arn:aws:iam::000000000000:role/{project.name}-deployer",
            developer_role_arn=f"arn:aws:iam::000000000000:role/{project.name}-developer",
            readonly_role_arn=f"arn:aws:iam::000000000000:role/{project.name}-readonly",
        )


class FakeLocalProvisioner:
    async def provision(self, request):
        return LocalProvisioningResult(resource_arn=f"arn:aws:s3:::{request.resource_name}")


def sign_in(client: TestClient) -> None:
    client.post(
        "/api/v1/auth/session",
        json={
            "principal_arn": "arn:aws:sts::000000000000:assumed-role/team-lead/test",
            "platform_role": "Team_Lead",
            "role_tags": {
                "display_name": "Project Lead",
                "email": "lead@example.test",
                "team": "platform",
            },
        },
    )


def test_approve_provisions_local_s3_request() -> None:
    app.dependency_overrides[get_project_iam_scaffolder] = FakeProjectIamScaffolder
    app.dependency_overrides[get_local_resource_provisioner] = FakeLocalProvisioner
    with TestClient(app) as client:
        sign_in(client)
        project = client.post(
            "/api/v1/projects",
            json={
                "name": f"project-{uuid.uuid4().hex[:8]}",
                "application_name": "portal-lab",
                "team_name": "platform",
                "cost_center": "engineering",
                "allowed_environments": ["dev"],
                "allowed_resource_types": ["s3"],
                "monthly_budget_usd": 100,
                "tags": {},
            },
        ).json()["data"]
        request = client.post(
            "/api/v1/requests",
            json={
                "project_id": project["id"],
                "resource_type": "s3",
                "name_suffix": "artifacts",
                "region": "us-east-1",
                "environment": "dev",
                "resource_config": {
                    "block_public_access": True,
                    "versioning_enabled": True,
                    "encryption": "SSE-S3",
                    "lifecycle_policy": {"enabled": True},
                    "logging_enabled": True,
                },
                "tags": {"owner": "lead@example.test"},
                "expiry_date": (date.today() + timedelta(days=30)).isoformat(),
            },
        ).json()["data"]
        approved = client.post(f"/api/v1/approvals/{request['id']}/approve")

    assert approved.status_code == 200
    assert approved.json()["data"]["status"] == "provisioned"
    assert approved.json()["data"]["provisioned_arn"].startswith("arn:aws:s3:::")
    app.dependency_overrides.clear()


def test_already_approved_request_can_be_provisioned_locally() -> None:
    app.dependency_overrides[get_project_iam_scaffolder] = FakeProjectIamScaffolder
    app.dependency_overrides[get_local_resource_provisioner] = FakeLocalProvisioner
    with TestClient(app) as client:
        sign_in(client)
        project = client.post(
            "/api/v1/projects",
            json={
                "name": f"project-{uuid.uuid4().hex[:8]}",
                "application_name": "portal-lab",
                "team_name": "platform",
                "cost_center": "engineering",
                "allowed_environments": ["dev"],
                "allowed_resource_types": ["s3"],
                "monthly_budget_usd": 100,
                "tags": {},
            },
        ).json()["data"]
        request = client.post(
            "/api/v1/requests",
            json={
                "project_id": project["id"],
                "resource_type": "s3",
                "name_suffix": "logs",
                "region": "us-east-1",
                "environment": "dev",
                "resource_config": {
                    "block_public_access": True,
                    "versioning_enabled": True,
                    "encryption": "SSE-S3",
                    "lifecycle_policy": {"enabled": True},
                    "logging_enabled": True,
                },
                "tags": {"owner": "lead@example.test"},
                "expiry_date": (date.today() + timedelta(days=30)).isoformat(),
            },
        ).json()["data"]
        first = client.post(f"/api/v1/approvals/{request['id']}/approve")
        second = client.post(f"/api/v1/approvals/{request['id']}/approve")

    assert first.json()["data"]["status"] == "provisioned"
    assert second.status_code == 200
    assert second.json()["data"]["status"] == "provisioned"
    app.dependency_overrides.clear()

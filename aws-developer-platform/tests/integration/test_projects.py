"""Project onboarding integration tests.

Validates Requirement 14 and task 8.3.
"""

import uuid

from fastapi.testclient import TestClient

from app.main import app
from app.services.project_iam import ProjectIamRoles, get_project_iam_scaffolder


class FakeProjectIamScaffolder:
    async def scaffold(self, project):
        return ProjectIamRoles(
            deployer_role_arn=f"arn:aws:iam::000000000000:role/{project.name}-deployer",
            developer_role_arn=f"arn:aws:iam::000000000000:role/{project.name}-developer",
            readonly_role_arn=f"arn:aws:iam::000000000000:role/{project.name}-readonly",
        )


def sign_in(client: TestClient, *, team: str = "platform") -> None:
    client.post(
        "/api/v1/auth/session",
        json={
            "principal_arn": "arn:aws:sts::000000000000:assumed-role/team-lead/test",
            "platform_role": "Team_Lead",
            "role_tags": {
                "display_name": "Project Lead",
                "email": "lead@example.test",
                "team": team,
            },
        },
    )


def project_payload(name: str, team: str = "platform") -> dict[str, object]:
    return {
        "name": name,
        "description": "Onboarding test",
        "application_name": "portal-lab",
        "team_name": team,
        "cost_center": "engineering",
        "allowed_environments": ["dev", "uat"],
        "allowed_resource_types": ["s3", "lambda", "dynamodb"],
        "monthly_budget_usd": 100,
        "tags": {},
    }


def test_team_lead_can_register_update_and_deactivate_project() -> None:
    name = f"project-{uuid.uuid4().hex[:8]}"
    app.dependency_overrides[get_project_iam_scaffolder] = FakeProjectIamScaffolder
    with TestClient(app) as client:
        sign_in(client)
        created = client.post("/api/v1/projects", json=project_payload(name))
        project_id = created.json()["data"]["id"]
        updated = client.patch(
            f"/api/v1/projects/{project_id}",
            json={"description": "Updated", "allowed_environments": ["dev"]},
        )
        deactivated = client.post(f"/api/v1/projects/{project_id}/deactivate")
        catalogue = client.get("/api/v1/projects")

    assert created.status_code == 201
    assert created.json()["data"]["default_owner"].endswith("/test")
    assert created.json()["data"]["deployer_role_arn"].endswith(f"{name}-deployer")
    assert updated.status_code == 200
    assert updated.json()["data"]["description"] == "Updated"
    assert deactivated.json()["data"]["status"] == "deactivated"
    assert name not in {project["name"] for project in catalogue.json()["data"]}
    app.dependency_overrides.clear()


def test_duplicate_project_name_returns_conflict() -> None:
    name = f"project-{uuid.uuid4().hex[:8]}"
    app.dependency_overrides[get_project_iam_scaffolder] = FakeProjectIamScaffolder
    with TestClient(app) as client:
        sign_in(client)
        first = client.post("/api/v1/projects", json=project_payload(name))
        duplicate = client.post("/api/v1/projects", json=project_payload(name))

    assert first.status_code == 201
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["message"] == "project name already exists"
    app.dependency_overrides.clear()


def test_project_is_marked_iam_failed_when_scaffolding_fails() -> None:
    class FailingProjectIamScaffolder:
        async def scaffold(self, project):
            raise RuntimeError(f"MiniStack unavailable for {project.name}")

    name = f"project-{uuid.uuid4().hex[:8]}"
    app.dependency_overrides[get_project_iam_scaffolder] = FailingProjectIamScaffolder
    with TestClient(app) as client:
        sign_in(client)
        created = client.post("/api/v1/projects", json=project_payload(name))

    assert created.status_code == 201
    assert created.json()["data"]["status"] == "iam_failed"
    assert "MiniStack unavailable" in created.json()["data"]["iam_error_details"]
    app.dependency_overrides.clear()

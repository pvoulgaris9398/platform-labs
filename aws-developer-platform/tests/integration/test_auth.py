"""Authentication endpoint integration tests."""

from fastapi.testclient import TestClient

from app.main import app


def test_development_sign_in_sets_session_and_returns_identity() -> None:
    """A fresh browser can sign in without any project setup."""

    payload = {
        "principal_arn": "arn:aws:sts::000000000000:assumed-role/platform-team_lead/browser",
        "platform_role": "Team_Lead",
        "role_tags": {
            "display_name": "Local Walkthrough User",
            "email": "local@example.test",
            "team": "platform",
        },
    }

    with TestClient(app) as client:
        sign_in = client.post("/api/v1/auth/session", json=payload)
        identity = client.get("/api/v1/auth/me")

    assert sign_in.status_code == 201
    assert sign_in.json()["data"]["role"] == "Team_Lead"
    assert "platform_session" in sign_in.cookies
    assert identity.status_code == 200
    assert identity.json()["data"]["email"] == "local@example.test"

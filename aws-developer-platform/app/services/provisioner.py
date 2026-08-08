"""Terraform Cloud client and webhook helpers."""

import hashlib
import hmac
from typing import Any

import httpx


def verify_signature(body: bytes, signature: str, secret: str) -> bool:
    """Constant-time verification for HMAC-SHA256 webhooks."""

    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    supplied = signature.removeprefix("sha256=")
    return hmac.compare_digest(expected, supplied)


class TerraformCloudClient:
    """Minimal typed adapter for Terraform Cloud run operations."""

    def __init__(self, base_url: str, token: str, client: httpx.AsyncClient | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.client = client or httpx.AsyncClient(timeout=15)

    async def create_run(self, workspace_id: str, message: str, variables: dict[str, Any]) -> str:
        """Create a Terraform Cloud run and return its ID."""

        payload = {
            "data": {
                "type": "runs",
                "attributes": {"message": message, "variables": variables},
                "relationships": {
                    "workspace": {"data": {"type": "workspaces", "id": workspace_id}}
                },
            }
        }
        response = await self.client.post(
            f"{self.base_url}/api/v2/runs",
            json=payload,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/vnd.api+json",
            },
        )
        response.raise_for_status()
        return str(response.json()["data"]["id"])

    async def run_status(self, run_id: str) -> str:
        """Return the current Terraform Cloud run status."""

        response = await self.client.get(
            f"{self.base_url}/api/v2/runs/{run_id}",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        response.raise_for_status()
        return str(response.json()["data"]["attributes"]["status"])

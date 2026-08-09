"""Project IAM scaffolding adapters."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlencode

import httpx

from app.config import get_settings
from app.db.models import Project
from app.services.iam_policy import build_policy


@dataclass(frozen=True)
class ProjectIamRoles:
    """Role ARNs created for a registered project."""

    deployer_role_arn: str
    developer_role_arn: str
    readonly_role_arn: str


class ProjectIamScaffolder(Protocol):
    """Create the initial IAM roles for a project registration."""

    async def scaffold(self, project: Project) -> ProjectIamRoles:
        """Create project IAM roles and return their ARNs."""


class ProjectIamScaffoldingError(RuntimeError):
    """Raised when project IAM scaffolding cannot be completed."""


class MiniStackProjectIamScaffolder:
    """Create project IAM roles against a local MiniStack endpoint."""

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

    async def scaffold(self, project: Project) -> ProjectIamRoles:
        """Create deployer, developer, and readonly roles for a project."""

        role_arns: dict[str, str] = {}
        for role_kind in ("deployer", "developer", "readonly"):
            role_name = f"{project.name}-{role_kind}"
            role_arns[role_kind] = await self._ensure_role(project, role_name)
            await self._put_inline_policy(role_name, role_kind)

        return ProjectIamRoles(
            deployer_role_arn=role_arns["deployer"],
            developer_role_arn=role_arns["developer"],
            readonly_role_arn=role_arns["readonly"],
        )

    async def _ensure_role(self, project: Project, role_name: str) -> str:
        assume_role_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": f"arn:aws:iam::{self.account_id}:root"},
                    "Action": "sts:AssumeRole",
                }
            ],
        }
        params = {
            "Action": "CreateRole",
            "Version": "2010-05-08",
            "RoleName": role_name,
            "AssumeRolePolicyDocument": json.dumps(assume_role_policy),
            "Description": f"Local POC role for {project.name}",
            "Tags.member.1.Key": "project",
            "Tags.member.1.Value": project.name,
            "Tags.member.2.Key": "team",
            "Tags.member.2.Value": project.team_name,
            "Tags.member.3.Key": "cost_center",
            "Tags.member.3.Value": project.cost_center,
        }
        response = await self._iam_request(params)
        if response.status_code == 409 or "EntityAlreadyExists" in response.text:
            return f"arn:aws:iam::{self.account_id}:role/{role_name}"
        if response.status_code >= 400:
            raise ProjectIamScaffoldingError(f"MiniStack CreateRole failed for {role_name}")

        arn = self._find_xml_text(response.text, "Arn")
        return arn or f"arn:aws:iam::{self.account_id}:role/{role_name}"

    async def _put_inline_policy(self, role_name: str, role_kind: str) -> None:
        policy = build_policy(role_kind, {"s3": [], "lambda": [], "dynamodb": []})
        params = {
            "Action": "PutRolePolicy",
            "Version": "2010-05-08",
            "RoleName": role_name,
            "PolicyName": f"{role_name}-initial",
            "PolicyDocument": json.dumps(policy),
        }
        response = await self._iam_request(params)
        if response.status_code >= 400:
            raise ProjectIamScaffoldingError(f"MiniStack PutRolePolicy failed for {role_name}")

    async def _iam_request(self, params: dict[str, str]) -> httpx.Response:
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": (
                "AWS4-HMAC-SHA256 Credential=test/20200101/"
                f"{self.region}/iam/aws4_request, SignedHeaders=host, Signature=test"
            ),
            "X-Amz-Date": "20200101T000000Z",
        }
        return await self.client.post(self.endpoint, content=urlencode(params), headers=headers)

    @staticmethod
    def _find_xml_text(payload: str, tag_name: str) -> str | None:
        match = re.search(rf"<(?:[A-Za-z0-9_]+:)?{tag_name}>([^<]+)</", payload)
        return match.group(1) if match else None


class DisabledProjectIamScaffolder:
    """Skip project IAM scaffolding for tests or deliberately DB-only demos."""

    async def scaffold(self, project: Project) -> ProjectIamRoles:
        """Return deterministic local ARNs without touching an external service."""

        settings = get_settings()
        return ProjectIamRoles(
            deployer_role_arn=f"arn:aws:iam::{settings.ministack_account_id}:role/{project.name}-deployer",
            developer_role_arn=f"arn:aws:iam::{settings.ministack_account_id}:role/{project.name}-developer",
            readonly_role_arn=f"arn:aws:iam::{settings.ministack_account_id}:role/{project.name}-readonly",
        )


def get_project_iam_scaffolder() -> ProjectIamScaffolder:
    """Return the configured project IAM scaffolding adapter."""

    settings = get_settings()
    if settings.project_iam_backend == "disabled":
        return DisabledProjectIamScaffolder()
    return MiniStackProjectIamScaffolder(
        endpoint=settings.ministack_endpoint,
        region=settings.aws_region,
        account_id=settings.ministack_account_id,
    )

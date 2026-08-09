"""Least-privilege IAM policy generation."""

from collections.abc import Iterable
from typing import Any

ROLE_ACTIONS = {
    "deployer": {
        "s3": ["s3:CreateBucket", "s3:DeleteBucket", "s3:PutBucketTagging"],
        "lambda": ["lambda:CreateFunction", "lambda:UpdateFunctionCode", "lambda:DeleteFunction"],
        "dynamodb": ["dynamodb:CreateTable", "dynamodb:UpdateTable", "dynamodb:DeleteTable"],
        "aurora": ["rds:CreateDBCluster", "rds:ModifyDBCluster", "rds:DeleteDBCluster"],
        "rds_postgresql": ["rds:CreateDBInstance", "rds:ModifyDBInstance", "rds:DeleteDBInstance"],
    },
    "developer": {
        "s3": ["s3:GetObject", "s3:ListBucket"],
        "lambda": ["lambda:GetFunction", "lambda:InvokeFunction"],
        "dynamodb": [
            "dynamodb:DescribeTable",
            "dynamodb:GetItem",
            "dynamodb:Query",
            "dynamodb:Scan",
        ],
        "aurora": ["rds:DescribeDBClusters"],
        "rds_postgresql": ["rds:DescribeDBInstances"],
    },
    "readonly": {
        "s3": ["s3:GetObject", "s3:ListBucket"],
        "lambda": ["lambda:GetFunction"],
        "dynamodb": ["dynamodb:DescribeTable", "dynamodb:GetItem", "dynamodb:Query"],
        "aurora": ["rds:DescribeDBClusters"],
        "rds_postgresql": ["rds:DescribeDBInstances"],
    },
}


def build_policy(role: str, resources: dict[str, Iterable[str]]) -> dict[str, Any]:
    """Build a policy containing only supplied ARNs and role-approved actions."""

    if role not in ROLE_ACTIONS:
        raise ValueError(f"unsupported role: {role}")
    statements = []
    for resource_type, arns in resources.items():
        arn_list = sorted(set(arns))
        if arn_list:
            statements.append(
                {
                    "Sid": resource_type.title(),
                    "Effect": "Allow",
                    "Action": ROLE_ACTIONS[role][resource_type],
                    "Resource": arn_list,
                }
            )
    return {"Version": "2012-10-17", "Statement": statements}

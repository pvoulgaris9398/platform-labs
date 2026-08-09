import { describe, expect, test } from 'vitest';

import { buildResourceLink } from './resourceLinks';
import type { ResourceRequest } from './types';

function request(overrides: Partial<ResourceRequest>): ResourceRequest {
  return {
    id: '00000000-0000-0000-0000-000000000001',
    project_id: '00000000-0000-0000-0000-000000000002',
    resource_type: 's3',
    resource_name: 'platform-demo-dev-artifacts',
    region: 'us-east-1',
    environment: 'dev',
    status: 'provisioned',
    estimated_monthly_cost_usd: '0.00',
    provisioned_arn: 'arn:aws:s3:::platform-demo-dev-artifacts',
    guardrail_warnings: [],
    expiry_date: '2026-09-08',
    ...overrides,
  };
}

describe('buildResourceLink', () => {
  test('returns null for unprovisioned requests', () => {
    expect(buildResourceLink(request({ status: 'approval_pending' }), 'http://localhost:4566')).toBeNull();
  });

  test('derives the resource service from provisioned ARN before resource type', () => {
    const link = buildResourceLink(
      request({
        resource_type: 's3',
        resource_name: 'platform-demo-dev-postgres',
        provisioned_arn: 'arn:aws:rds:us-east-1:000000000000:db:platform-demo-dev-postgres',
      }),
      'http://localhost:4566',
    );

    expect(link?.label).toBe(
      'https://us-east-1.console.aws.amazon.com/rds/home?region=us-east-1#database:id=platform-demo-dev-postgres;is-cluster=false',
    );
  });
});

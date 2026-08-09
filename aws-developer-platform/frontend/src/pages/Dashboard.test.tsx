import '@testing-library/jest-dom/vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { cleanup, render, screen } from '@testing-library/react';
import { afterAll, afterEach, beforeAll, expect, test } from 'vitest';
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';

import { Dashboard } from './Dashboard';

const server = setupServer(http.get('/api/v1/requests', () => HttpResponse.json({ data: [], error: null })));
beforeAll(() => server.listen());
afterEach(() => {
  cleanup();
  server.resetHandlers();
});
afterAll(() => server.close());

test('renders an explicit empty state', async () => {
  render(<QueryClientProvider client={new QueryClient()}><Dashboard /></QueryClientProvider>);
  expect(await screen.findByText('No requests yet.')).toBeInTheDocument();
});

test('links provisioned s3 requests to the local MiniStack bucket URL', async () => {
  server.use(
    http.get('/api/v1/requests', () => HttpResponse.json({
      data: [{
        id: '00000000-0000-0000-0000-000000000001',
        project_id: '00000000-0000-0000-0000-000000000002',
        resource_type: 's3',
        resource_name: 'platform-demo-dev-artifacts',
        region: 'us-east-1',
        environment: 'dev',
        status: 'provisioned',
        estimated_monthly_cost_usd: '0.00',
        guardrail_warnings: [],
        expiry_date: '2026-09-08',
        provisioned_arn: 'arn:aws:s3:::platform-demo-dev-artifacts',
      }],
      error: null,
    })),
  );

  render(<QueryClientProvider client={new QueryClient()}><Dashboard /></QueryClientProvider>);

  expect(
    await screen.findByRole('link', {
      name: 'https://platform-demo-dev-artifacts.s3.us-east-1.amazonaws.com',
    }),
  ).toHaveAttribute(
    'href',
    'http://localhost:4566/platform-demo-dev-artifacts',
  );
});

test('links provisioned lambda requests to a lambda-shaped local URL', async () => {
  server.use(
    http.get('/api/v1/requests', () => HttpResponse.json({
      data: [{
        id: '00000000-0000-0000-0000-000000000003',
        project_id: '00000000-0000-0000-0000-000000000004',
        resource_type: 'lambda',
        resource_name: 'platform-demo-dev-worker',
        region: 'us-east-1',
        environment: 'dev',
        status: 'provisioned',
        estimated_monthly_cost_usd: '0.00',
        guardrail_warnings: [],
        expiry_date: '2026-09-08',
        provisioned_arn: 'arn:aws:lambda:us-east-1:000000000000:function:platform-demo-dev-worker',
      }],
      error: null,
    })),
  );

  render(<QueryClientProvider client={new QueryClient()}><Dashboard /></QueryClientProvider>);

  expect(
    await screen.findByRole('link', {
      name: 'https://us-east-1.console.aws.amazon.com/lambda/home?region=us-east-1#/functions/platform-demo-dev-worker',
    }),
  ).toHaveAttribute(
    'href',
    'http://localhost:4566/2015-03-31/functions/platform-demo-dev-worker',
  );
});

test('shows service-specific aws-style links for dynamodb aurora and rds postgresql', async () => {
  server.use(
    http.get('/api/v1/requests', () => HttpResponse.json({
      data: [
        {
          id: '00000000-0000-0000-0000-000000000005',
          project_id: '00000000-0000-0000-0000-000000000006',
          resource_type: 'dynamodb',
          resource_name: 'platform.demo.dev.Sessions',
          region: 'us-east-1',
          environment: 'dev',
          status: 'provisioned',
          estimated_monthly_cost_usd: '0.00',
          guardrail_warnings: [],
          expiry_date: '2026-09-08',
          provisioned_arn: 'arn:aws:dynamodb:us-east-1:000000000000:table/platform.demo.dev.Sessions',
        },
        {
          id: '00000000-0000-0000-0000-000000000007',
          project_id: '00000000-0000-0000-0000-000000000008',
          resource_type: 'aurora',
          resource_name: 'platform-demo-dev-db',
          region: 'us-east-1',
          environment: 'dev',
          status: 'provisioned',
          estimated_monthly_cost_usd: '87.60',
          guardrail_warnings: [],
          expiry_date: '2026-09-08',
          provisioned_arn: 'arn:aws:rds:us-east-1:000000000000:cluster:platform-demo-dev-db',
        },
        {
          id: '00000000-0000-0000-0000-000000000009',
          project_id: '00000000-0000-0000-0000-000000000010',
          resource_type: 'rds_postgresql',
          resource_name: 'platform-demo-dev-postgres',
          region: 'us-east-1',
          environment: 'dev',
          status: 'provisioned',
          estimated_monthly_cost_usd: '58.40',
          guardrail_warnings: [],
          expiry_date: '2026-09-08',
          provisioned_arn: 'arn:aws:rds:us-east-1:000000000000:db:platform-demo-dev-postgres',
        },
      ],
      error: null,
    })),
  );

  render(<QueryClientProvider client={new QueryClient()}><Dashboard /></QueryClientProvider>);

  expect(
    await screen.findByRole('link', {
      name: 'https://us-east-1.console.aws.amazon.com/dynamodbv2/home?region=us-east-1#table?name=platform.demo.dev.Sessions',
    }),
  ).toBeInTheDocument();
  expect(
    await screen.findByRole('link', {
      name: 'https://us-east-1.console.aws.amazon.com/rds/home?region=us-east-1#database:id=platform-demo-dev-db;is-cluster=true',
    }),
  ).toBeInTheDocument();
  expect(
    await screen.findByRole('link', {
      name: 'https://us-east-1.console.aws.amazon.com/rds/home?region=us-east-1#database:id=platform-demo-dev-postgres;is-cluster=false',
    }),
  ).toBeInTheDocument();
});

test('derives the dashboard link service from provisioned arn before resource type', async () => {
  server.use(
    http.get('/api/v1/requests', () => HttpResponse.json({
      data: [{
        id: '00000000-0000-0000-0000-000000000011',
        project_id: '00000000-0000-0000-0000-000000000012',
        resource_type: 's3',
        resource_name: 'platform-demo-dev-postgres',
        region: 'us-east-1',
        environment: 'dev',
        status: 'provisioned',
        estimated_monthly_cost_usd: '58.40',
        guardrail_warnings: [],
        expiry_date: '2026-09-08',
        provisioned_arn: 'arn:aws:rds:us-east-1:000000000000:db:platform-demo-dev-postgres',
      }],
      error: null,
    })),
  );

  render(<QueryClientProvider client={new QueryClient()}><Dashboard /></QueryClientProvider>);

  expect(
    await screen.findByRole('link', {
      name: 'https://us-east-1.console.aws.amazon.com/rds/home?region=us-east-1#database:id=platform-demo-dev-postgres;is-cluster=false',
    }),
  ).toBeInTheDocument();
  expect(screen.queryByText(/s3\.us-east-1\.amazonaws\.com/)).not.toBeInTheDocument();
});

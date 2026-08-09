import '@testing-library/jest-dom/vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { afterAll, afterEach, beforeAll, expect, test } from 'vitest';
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';

import { Dashboard } from './Dashboard';

const server = setupServer(http.get('/api/v1/requests', () => HttpResponse.json({ data: [], error: null })));
beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
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

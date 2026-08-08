import '@testing-library/jest-dom/vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { afterAll, beforeAll, expect, test } from 'vitest';
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';

import { Dashboard } from './Dashboard';

const server = setupServer(http.get('/api/v1/requests', () => HttpResponse.json({ data: [], error: null })));
beforeAll(() => server.listen()); afterAll(() => server.close());

test('renders an explicit empty state', async () => {
  render(<QueryClientProvider client={new QueryClient()}><Dashboard /></QueryClientProvider>);
  expect(await screen.findByText('No requests yet.')).toBeInTheDocument();
});

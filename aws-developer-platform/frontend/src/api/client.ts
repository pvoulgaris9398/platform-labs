import type { Envelope } from './types';

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  });
  const contentType = response.headers.get('content-type') ?? '';
  if (!contentType.includes('application/json')) {
    throw new ApiError(
      response.ok ? 'API returned an unexpected response' : `API request failed (${response.status})`,
      response.status,
    );
  }
  const body = (await response.json()) as Envelope<T>;
  if (!response.ok || body.error || body.data === null) {
    throw new ApiError(body.error?.message ?? 'Request failed', response.status);
  }
  return body.data;
}

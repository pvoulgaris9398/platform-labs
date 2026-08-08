import { Alert, CircularProgress } from '@mui/material';
import { useQuery } from '@tanstack/react-query';
import { Navigate } from 'react-router';

import { api, ApiError } from '../api/client';
import type { Identity } from '../api/types';
import { useSession } from '../store/session';
import { Layout } from './Layout';

export function ProtectedLayout(): React.JSX.Element {
  const setSession = useSession((state) => state.setSession);
  const identity = useQuery({
    queryKey: ['identity'],
    queryFn: async () => {
      const value = await api<Identity>('/auth/me');
      setSession(value.principal_arn, value.role);
      return value;
    },
    retry: false,
  });

  if (identity.isPending) return <CircularProgress aria-label="Checking session" />;
  if (identity.error instanceof ApiError && identity.error.status === 401) {
    return <Navigate to="/login" replace />;
  }
  if (identity.isError) {
    return <Alert severity="error">{identity.error.message}</Alert>;
  }
  return <Layout />;
}

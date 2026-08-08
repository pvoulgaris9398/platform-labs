import { Alert, Button, Container, MenuItem, Stack, TextField, Typography } from '@mui/material';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useNavigate } from 'react-router';

import { api } from '../api/client';
import type { Identity } from '../api/types';

export function Login(): React.JSX.Element {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [role, setRole] = useState<Identity['role']>('Team_Lead');
  const login = useMutation({
    mutationFn: () => api<Identity>('/auth/session', {
      method: 'POST',
      body: JSON.stringify({
        principal_arn: `arn:aws:sts::000000000000:assumed-role/platform-${role.toLowerCase()}/browser`,
        platform_role: role,
        role_tags: {
          display_name: 'Local Walkthrough User',
          email: 'local@example.test',
          team: 'platform',
        },
      }),
    }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['identity'] });
      navigate('/projects');
    },
  });

  return <Container maxWidth="sm" sx={{ py: 8 }}><Stack spacing={3}><Typography variant="h3">Local sign in</Typography><Alert severity="info">This development-only sign-in is disabled in deployed environments.</Alert>{login.isError && <Alert severity="error">{login.error.message}</Alert>}<TextField select label="Platform role" value={role} onChange={(event) => setRole(event.target.value as Identity['role'])}><MenuItem value="Developer">Developer</MenuItem><MenuItem value="Team_Lead">Team lead</MenuItem><MenuItem value="Platform_Admin">Platform admin</MenuItem></TextField><Button variant="contained" onClick={() => login.mutate()} disabled={login.isPending}>{login.isPending ? 'Signing in…' : 'Sign in'}</Button></Stack></Container>;
}

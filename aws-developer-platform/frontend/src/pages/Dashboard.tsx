import { Alert, CircularProgress, List, ListItem, ListItemText, Typography } from '@mui/material';
import { useQuery } from '@tanstack/react-query';

import { api } from '../api/client';
import type { ResourceRequest } from '../api/types';

export function Dashboard(): React.JSX.Element {
  const requests = useQuery({ queryKey: ['requests'], queryFn: () => api<ResourceRequest[]>('/requests') });
  if (requests.isPending) return <CircularProgress aria-label="Loading requests" />;
  if (requests.isError) return <Alert severity="error">Unable to load requests.</Alert>;
  return <><Typography variant="h4" gutterBottom>My requests</Typography>{requests.data.length === 0 ? <Typography>No requests yet.</Typography> : <List>{requests.data.map((request) => <ListItem key={request.id}><ListItemText primary={request.resource_name} secondary={`${request.resource_type} — ${request.status}`} /></ListItem>)}</List>}</>;
}

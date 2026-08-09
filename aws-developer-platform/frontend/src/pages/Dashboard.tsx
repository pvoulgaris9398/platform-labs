import { Alert, CircularProgress, Link, List, ListItem, ListItemText, Stack, Typography } from '@mui/material';
import { useQuery } from '@tanstack/react-query';

import { api } from '../api/client';
import { buildResourceLink } from '../api/resourceLinks';
import type { ResourceRequest } from '../api/types';

const ministackEndpoint = import.meta.env.VITE_MINISTACK_ENDPOINT ?? 'http://localhost:4566';

export function Dashboard(): React.JSX.Element {
  const requests = useQuery({ queryKey: ['requests'], queryFn: () => api<ResourceRequest[]>('/requests') });
  if (requests.isPending) return <CircularProgress aria-label="Loading requests" />;
  if (requests.isError) return <Alert severity="error">Unable to load requests.</Alert>;
  return <><Typography variant="h4" gutterBottom>My requests</Typography>{requests.data.length === 0 ? <Typography>No requests yet.</Typography> : <List>{requests.data.map((request) => {
    const link = buildResourceLink(request, ministackEndpoint);
    return <ListItem key={request.id}><ListItemText primary={request.resource_name} secondary={<Stack component="span" spacing={0.5}><span>{request.resource_type} - {request.status}</span>{link && <Link href={link.href} target="_blank" rel="noreferrer">{link.label}</Link>}</Stack>} /></ListItem>;
  })}</List>}</>;
}

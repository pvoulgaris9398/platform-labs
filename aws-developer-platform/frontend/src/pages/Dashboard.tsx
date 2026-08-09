import { Alert, CircularProgress, Link, List, ListItem, ListItemText, Stack, Typography } from '@mui/material';
import { useQuery } from '@tanstack/react-query';

import { api } from '../api/client';
import type { ResourceRequest } from '../api/types';

const ministackEndpoint = import.meta.env.VITE_MINISTACK_ENDPOINT ?? 'http://localhost:4566';

function resourceUrl(request: ResourceRequest): string | null {
  if (request.status !== 'provisioned' || request.resource_type !== 's3') return null;
  return `${ministackEndpoint.replace(/\/$/, '')}/${request.resource_name}`;
}

function awsLikeResourceUrl(request: ResourceRequest): string | null {
  if (request.status !== 'provisioned' || request.resource_type !== 's3') return null;
  return `https://${request.resource_name}.s3.${request.region}.amazonaws.com`;
}

export function Dashboard(): React.JSX.Element {
  const requests = useQuery({ queryKey: ['requests'], queryFn: () => api<ResourceRequest[]>('/requests') });
  if (requests.isPending) return <CircularProgress aria-label="Loading requests" />;
  if (requests.isError) return <Alert severity="error">Unable to load requests.</Alert>;
  return <><Typography variant="h4" gutterBottom>My requests</Typography>{requests.data.length === 0 ? <Typography>No requests yet.</Typography> : <List>{requests.data.map((request) => {
    const url = resourceUrl(request);
    const awsUrl = awsLikeResourceUrl(request);
    return <ListItem key={request.id}><ListItemText primary={request.resource_name} secondary={<Stack component="span" spacing={0.5}><span>{request.resource_type} - {request.status}</span>{url && awsUrl && <Link href={url} target="_blank" rel="noreferrer">{awsUrl}</Link>}</Stack>} /></ListItem>;
  })}</List>}</>;
}

import { Alert, Button, CircularProgress, List, ListItem, ListItemText, Stack, Typography } from '@mui/material';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from '../api/client';
import type { ResourceRequest } from '../api/types';

export function Approvals(): React.JSX.Element {
  const client = useQueryClient();
  const queue = useQuery({ queryKey: ['approvals'], queryFn: () => api<ResourceRequest[]>('/approvals') });
  const approve = useMutation({ mutationFn: (id: string) => api<ResourceRequest>(`/approvals/${id}/approve`, { method: 'POST' }), onSuccess: async () => { await client.invalidateQueries({ queryKey: ['approvals'] }); } });
  if (queue.isPending) return <CircularProgress aria-label="Loading approvals" />;
  if (queue.isError) return <Alert severity="error">Unable to load the approval queue.</Alert>;
  return <><Typography variant="h4">Approval queue</Typography>{queue.data.length === 0 ? <Typography>No requests await approval.</Typography> : <List>{queue.data.map((request) => <ListItem key={request.id} secondaryAction={<Button onClick={() => approve.mutate(request.id)}>Approve</Button>}><ListItemText primary={request.resource_name} secondary={<Stack component="span"><span>{request.resource_type}</span><span>Estimated monthly cost: ${request.estimated_monthly_cost_usd ?? 'unknown'}</span></Stack>} /></ListItem>)}</List>}</>;
}

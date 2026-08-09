import { Alert, Chip, CircularProgress, Divider, List, ListItem, ListItemText, Stack, Typography } from '@mui/material';
import { useQuery } from '@tanstack/react-query';

import { api, ApiError } from '../api/client';
import type { Project } from '../api/types';
import type { Identity } from '../api/types';
import { ProjectRegistrationForm } from '../components/ProjectRegistrationForm';

export function Projects(): React.JSX.Element {
  const projects = useQuery({ queryKey: ['projects'], queryFn: () => api<Project[]>('/projects') });
  const identity = useQuery({ queryKey: ['identity'], queryFn: () => api<Identity>('/auth/me') });
  if (projects.isPending || identity.isPending) return <CircularProgress aria-label="Loading projects" />;
  if (projects.isError) {
    const message = projects.error instanceof ApiError
      ? `Unable to load projects: ${projects.error.message}`
      : 'Unable to load projects.';
    return <Alert severity="error">{message}</Alert>;
  }
  if (identity.isError) return <Alert severity="error">Unable to load your project permissions.</Alert>;
  const canRegister = identity.data.role === 'Team_Lead' || identity.data.role === 'Platform_Admin';
  return <Stack spacing={3}><Typography variant="h4">Projects</Typography>{projects.data.length === 0 ? <Typography>No active projects registered for your team.</Typography> : <List>{projects.data.map((project) => <ListItem key={project.id} secondaryAction={<Chip label={project.status} color="success" size="small" />}><ListItemText primary={project.name} secondary={`${project.application_name} — ${project.team_name} — ${project.allowed_environments.join(', ')}`} /></ListItem>)}</List>}{canRegister && <><Divider /><ProjectRegistrationForm identity={identity.data} /></>}</Stack>;
}

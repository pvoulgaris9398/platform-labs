import { Alert, CircularProgress, List, ListItem, ListItemText, Typography } from '@mui/material';
import { useQuery } from '@tanstack/react-query';

import { api, ApiError } from '../api/client';
import type { Project } from '../api/types';

export function Projects(): React.JSX.Element {
  const projects = useQuery({ queryKey: ['projects'], queryFn: () => api<Project[]>('/projects') });
  if (projects.isPending) return <CircularProgress aria-label="Loading projects" />;
  if (projects.isError) {
    const message = projects.error instanceof ApiError
      ? `Unable to load projects: ${projects.error.message}`
      : 'Unable to load projects.';
    return <Alert severity="error">{message}</Alert>;
  }
  return <><Typography variant="h4">Projects</Typography>{projects.data.length === 0 ? <Typography>No projects registered.</Typography> : <List>{projects.data.map((project) => <ListItem key={project.id}><ListItemText primary={project.name} secondary={`${project.application_name} — ${project.team_name}`} /></ListItem>)}</List>}</>;
}

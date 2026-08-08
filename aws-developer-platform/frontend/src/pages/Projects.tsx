import { Alert, CircularProgress, List, ListItem, ListItemText, Typography } from '@mui/material';
import { useQuery } from '@tanstack/react-query';

import { api } from '../api/client';
import type { Project } from '../api/types';

export function Projects(): React.JSX.Element {
  const projects = useQuery({ queryKey: ['projects'], queryFn: () => api<Project[]>('/projects') });
  if (projects.isPending) return <CircularProgress aria-label="Loading projects" />;
  if (projects.isError) return <Alert severity="error">Unable to load projects.</Alert>;
  return <><Typography variant="h4">Projects</Typography>{projects.data.length === 0 ? <Typography>No projects registered.</Typography> : <List>{projects.data.map((project) => <ListItem key={project.id}><ListItemText primary={project.name} secondary={`${project.application_name} — ${project.team_name}`} /></ListItem>)}</List>}</>;
}

import { zodResolver } from '@hookform/resolvers/zod';
import { Alert, Button, CircularProgress, MenuItem, Stack, TextField, Typography } from '@mui/material';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Controller, useForm, useWatch } from 'react-hook-form';
import { useNavigate } from 'react-router';
import { z } from 'zod';

import { api } from '../api/client';
import { RESOURCE_TYPES, resourceTypeLabel } from '../api/resourceTypes';
import type { Project, ResourceRequest, ResourceType } from '../api/types';

type Environment = 'dev' | 'uat' | 'staging' | 'prod';

const environmentLabels = {
  dev: 'Development',
  uat: 'UAT',
  staging: 'Staging',
  prod: 'Production',
} as const;

function isEnvironment(value: string): value is Environment {
  return value in environmentLabels;
}

const schema = z.object({
  project_id: z.string().uuid('Choose a project'),
  resource_type: z.enum(RESOURCE_TYPES),
  name_suffix: z.string().min(1),
  region: z.string().min(1),
  environment: z.enum(['dev', 'uat', 'staging', 'prod']),
  owner: z.string().min(1),
  expiry_date: z.string().min(1),
});

type FormValues = z.infer<typeof schema>;

function defaultExpiryDate(): string {
  const date = new Date();
  date.setDate(date.getDate() + 30);
  return date.toISOString().slice(0, 10);
}

export function RequestWizard(): React.JSX.Element {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const projects = useQuery({ queryKey: ['projects'], queryFn: () => api<Project[]>('/projects') });
  const { control, handleSubmit, setValue, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      project_id: '',
      resource_type: 's3',
      name_suffix: '',
      region: 'us-east-1',
      environment: 'dev',
      owner: '',
      expiry_date: defaultExpiryDate(),
    },
  });
  const selectedProjectId = useWatch({ control, name: 'project_id' });
  const selectedProject = projects.data?.find((project) => project.id === selectedProjectId);
  const resourceTypes: readonly ResourceType[] = selectedProject?.allowed_resource_types ?? RESOURCE_TYPES;
  const environments: readonly Environment[] = selectedProject?.allowed_environments.filter(isEnvironment) ?? ['dev', 'uat'];

  const create = useMutation({
    mutationFn: (values: FormValues) => api<ResourceRequest>('/requests', {
      method: 'POST',
      body: JSON.stringify({
        ...values,
        resource_config: {},
        tags: { owner: values.owner },
      }),
    }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['requests'] });
      navigate('/dashboard');
    },
  });

  if (projects.isPending) return <CircularProgress aria-label="Loading projects" />;
  if (projects.isError) return <Alert severity="error">Unable to load available projects.</Alert>;

  return (
    <Stack component="form" spacing={2} onSubmit={handleSubmit((values) => create.mutate(values))} noValidate>
      <Typography variant="h4">New resource request</Typography>
      {projects.data.length === 0 && <Alert severity="info">No active projects are available for your team yet.</Alert>}
      {create.isError && <Alert severity="error">Request could not be submitted.</Alert>}
      <Controller
        name="project_id"
        control={control}
        render={({ field }) => (
          <TextField
            {...field}
            select
            label="Project"
            error={Boolean(errors.project_id)}
            helperText={errors.project_id?.message ?? selectedProject?.description}
            onChange={(event) => {
              field.onChange(event);
              const project = projects.data.find((item) => item.id === event.target.value);
              if (project) {
                setValue('owner', project.default_owner, { shouldValidate: true });
                setValue('resource_type', project.allowed_resource_types[0] ?? 's3', { shouldValidate: true });
                setValue('environment', project.allowed_environments.find(isEnvironment) ?? 'dev', { shouldValidate: true });
              }
            }}
          >
            {projects.data.map((project) => (
              <MenuItem key={project.id} value={project.id}>
                {project.name} - {project.application_name} ({project.team_name})
              </MenuItem>
            ))}
          </TextField>
        )}
      />
      <Controller
        name="resource_type"
        control={control}
        render={({ field }) => (
          <TextField {...field} select label="Resource type">
            {resourceTypes.map((resourceType) => (
              <MenuItem key={resourceType} value={resourceType}>{resourceTypeLabel(resourceType)}</MenuItem>
            ))}
          </TextField>
        )}
      />
      <Controller name="name_suffix" control={control} render={({ field }) => <TextField {...field} label="Name" error={Boolean(errors.name_suffix)} helperText={errors.name_suffix?.message} />} />
      <Controller name="region" control={control} render={({ field }) => <TextField {...field} label="AWS region" error={Boolean(errors.region)} helperText={errors.region?.message} />} />
      <Controller
        name="environment"
        control={control}
        render={({ field }) => (
          <TextField {...field} select label="Environment">
            {environments.map((environment) => (
              <MenuItem key={environment} value={environment}>{environmentLabels[environment]}</MenuItem>
            ))}
          </TextField>
        )}
      />
      <Controller name="owner" control={control} render={({ field }) => <TextField {...field} label="Owner" error={Boolean(errors.owner)} helperText={errors.owner?.message} />} />
      <Controller name="expiry_date" control={control} render={({ field }) => <TextField {...field} type="date" label="Expiry date" error={Boolean(errors.expiry_date)} helperText={errors.expiry_date?.message} slotProps={{ inputLabel: { shrink: true } }} />} />
      <Button type="submit" variant="contained" disabled={create.isPending || projects.data.length === 0}>
        {create.isPending ? 'Submitting...' : 'Submit request'}
      </Button>
    </Stack>
  );
}

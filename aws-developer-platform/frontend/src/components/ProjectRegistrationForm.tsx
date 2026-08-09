import { zodResolver } from '@hookform/resolvers/zod';
import {
  Alert,
  Button,
  Checkbox,
  FormControl,
  InputLabel,
  ListItemText,
  MenuItem,
  OutlinedInput,
  Select,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Controller, useForm } from 'react-hook-form';
import { z } from 'zod';

import { api, ApiError } from '../api/client';
import { RESOURCE_TYPES } from '../api/resourceTypes';
import type { Identity, Project, ResourceType } from '../api/types';

const environments = ['dev', 'uat', 'staging', 'prod'] as const;
const projectSchema = z.object({
  name: z.string().regex(/^[a-z0-9](?:[a-z0-9-]{0,30}[a-z0-9])?$/, 'Use lowercase letters, numbers, and internal hyphens (maximum 32 characters).'),
  description: z.string(),
  application_name: z.string().min(1, 'Application name is required.').max(128),
  team_name: z.string().min(1, 'Team name is required.').max(128),
  cost_center: z.string().min(1, 'Cost center is required.').max(64),
  default_owner: z.string().min(1, 'Default owner is required.').max(256),
  allowed_environments: z.array(z.enum(environments)).min(1, 'Select at least one environment.'),
  allowed_resource_types: z.array(z.enum(RESOURCE_TYPES)).min(1, 'Select at least one resource type.'),
  monthly_budget_usd: z.number().positive('Budget must be greater than zero.'),
});

type ProjectFormValues = z.infer<typeof projectSchema>;

export interface ProjectRegistrationFormProps {
  readonly identity: Identity;
}

export function ProjectRegistrationForm({ identity }: ProjectRegistrationFormProps): React.JSX.Element {
  const queryClient = useQueryClient();
  const { control, register, handleSubmit, reset, formState: { errors } } = useForm<ProjectFormValues>({
    resolver: zodResolver(projectSchema),
    mode: 'onBlur',
    defaultValues: {
      name: '', description: '', application_name: '', team_name: identity.team,
      cost_center: '', default_owner: identity.principal_arn,
      allowed_environments: ['dev', 'uat'], allowed_resource_types: [...RESOURCE_TYPES],
      monthly_budget_usd: 100,
    },
  });
  const createProject = useMutation({
    mutationFn: (values: ProjectFormValues) => api<Project>('/projects', {
      method: 'POST',
      body: JSON.stringify({ ...values, description: values.description || null }),
    }),
    onSuccess: async () => {
      reset();
      await queryClient.invalidateQueries({ queryKey: ['projects'] });
    },
  });
  const submit = (values: ProjectFormValues): void => createProject.mutate(values);

  return <Stack component="form" spacing={2} onSubmit={handleSubmit(submit)} noValidate>
    <Typography variant="h5">Onboard a project</Typography>
    {createProject.isSuccess && <Alert severity="success">Project registered successfully.</Alert>}
    {createProject.isError && <Alert severity="error">{createProject.error instanceof ApiError ? createProject.error.message : 'Unable to register project.'}</Alert>}
    <TextField label="Project name" {...register('name')} error={Boolean(errors.name)} helperText={errors.name?.message} />
    <TextField label="Description" multiline minRows={2} {...register('description')} />
    <TextField label="Application name" {...register('application_name')} error={Boolean(errors.application_name)} helperText={errors.application_name?.message} />
    <TextField label="Team name" {...register('team_name')} error={Boolean(errors.team_name)} helperText={errors.team_name?.message} />
    <TextField label="Cost center" {...register('cost_center')} error={Boolean(errors.cost_center)} helperText={errors.cost_center?.message} />
    <TextField label="Default owner" {...register('default_owner')} error={Boolean(errors.default_owner)} helperText={errors.default_owner?.message} />
    <Controller name="allowed_environments" control={control} render={({ field }) => <FormControl error={Boolean(errors.allowed_environments)}><InputLabel id="environments-label">Allowed environments</InputLabel><Select {...field} labelId="environments-label" multiple input={<OutlinedInput label="Allowed environments" />} renderValue={(selected) => selected.join(', ')}>{environments.map((value) => <MenuItem key={value} value={value}><Checkbox checked={field.value.includes(value)} /><ListItemText primary={value} /></MenuItem>)}</Select></FormControl>} />
    <Controller name="allowed_resource_types" control={control} render={({ field }) => <FormControl error={Boolean(errors.allowed_resource_types)}><InputLabel id="resource-types-label">Allowed resource types</InputLabel><Select {...field} labelId="resource-types-label" multiple input={<OutlinedInput label="Allowed resource types" />} renderValue={(selected: ResourceType[]) => selected.join(', ')}>{RESOURCE_TYPES.map((value) => <MenuItem key={value} value={value}><Checkbox checked={field.value.includes(value)} /><ListItemText primary={value} /></MenuItem>)}</Select></FormControl>} />
    <TextField label="Monthly budget (USD)" type="number" inputProps={{ min: 0.01, step: 0.01 }} {...register('monthly_budget_usd', { valueAsNumber: true })} error={Boolean(errors.monthly_budget_usd)} helperText={errors.monthly_budget_usd?.message} />
    <Button type="submit" variant="contained" disabled={createProject.isPending}>{createProject.isPending ? 'Registering…' : 'Register project'}</Button>
  </Stack>;
}

import { zodResolver } from '@hookform/resolvers/zod';
import { Alert, Button, MenuItem, Stack, TextField, Typography } from '@mui/material';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Controller, useForm } from 'react-hook-form';
import { useNavigate } from 'react-router';
import { z } from 'zod';

import { api } from '../api/client';
import type { ResourceRequest } from '../api/types';

const schema = z.object({
  project_id: z.string().uuid(), resource_type: z.enum(['s3', 'lambda', 'dynamodb']),
  name_suffix: z.string().min(1), region: z.string().min(1), environment: z.enum(['dev', 'uat', 'staging', 'prod']),
  owner: z.string().min(1), expiry_date: z.string().min(1),
});
type FormValues = z.infer<typeof schema>;

export function RequestWizard(): React.JSX.Element {
  const navigate = useNavigate(); const queryClient = useQueryClient();
  const { control, handleSubmit, formState: { errors } } = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: { project_id: '', resource_type: 's3', name_suffix: '', region: 'us-east-1', environment: 'dev', owner: '', expiry_date: '' } });
  const create = useMutation({ mutationFn: (values: FormValues) => api<ResourceRequest>('/requests', { method: 'POST', body: JSON.stringify({ ...values, resource_config: {}, tags: { owner: values.owner } }) }), onSuccess: async () => { await queryClient.invalidateQueries({ queryKey: ['requests'] }); navigate('/dashboard'); } });
  return <Stack component="form" spacing={2} onSubmit={handleSubmit((values) => create.mutate(values))} noValidate><Typography variant="h4">New resource request</Typography>{create.isError && <Alert severity="error">Request could not be submitted.</Alert>}<Controller name="project_id" control={control} render={({ field }) => <TextField {...field} label="Project ID" error={Boolean(errors.project_id)} helperText={errors.project_id?.message} />} /><Controller name="resource_type" control={control} render={({ field }) => <TextField {...field} select label="Resource type"><MenuItem value="s3">S3 bucket</MenuItem><MenuItem value="lambda">Lambda function</MenuItem><MenuItem value="dynamodb">DynamoDB table</MenuItem></TextField>} /><Controller name="name_suffix" control={control} render={({ field }) => <TextField {...field} label="Name" error={Boolean(errors.name_suffix)} />} /><Controller name="region" control={control} render={({ field }) => <TextField {...field} label="AWS region" />} /><Controller name="environment" control={control} render={({ field }) => <TextField {...field} select label="Environment"><MenuItem value="dev">Development</MenuItem><MenuItem value="uat">UAT</MenuItem><MenuItem value="staging">Staging</MenuItem><MenuItem value="prod">Production</MenuItem></TextField>} /><Controller name="owner" control={control} render={({ field }) => <TextField {...field} label="Owner" />} /><Controller name="expiry_date" control={control} render={({ field }) => <TextField {...field} type="date" label="Expiry date" slotProps={{ inputLabel: { shrink: true } }} />} /><Button type="submit" variant="contained" disabled={create.isPending}>Submit request</Button></Stack>;
}

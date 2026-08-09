export const RESOURCE_TYPES = ['s3', 'lambda', 'dynamodb', 'aurora', 'rds_postgresql'] as const;

export type ResourceType = typeof RESOURCE_TYPES[number];

export function isResourceType(value: string): value is ResourceType {
  return RESOURCE_TYPES.some((resourceType) => resourceType === value);
}

export const ResourceTypes = {
  S3: 's3',
  Lambda: 'lambda',
  DynamoDB: 'dynamodb',
  Aurora: 'aurora',
  RdsPostgreSQL: 'rds_postgresql',
} as const;

export type S3ResourceType = typeof ResourceTypes.S3;
export type LambdaResourceType = typeof ResourceTypes.Lambda;
export type DynamoDBResourceType = typeof ResourceTypes.DynamoDB;
export type AuroraResourceType = typeof ResourceTypes.Aurora;
export type RdsPostgreSQLResourceType = typeof ResourceTypes.RdsPostgreSQL;

export type ResourceType =
  | S3ResourceType
  | LambdaResourceType
  | DynamoDBResourceType
  | AuroraResourceType
  | RdsPostgreSQLResourceType;

export type ResourceTypeDefinition =
  | { readonly value: S3ResourceType; readonly label: 'S3 bucket' }
  | { readonly value: LambdaResourceType; readonly label: 'Lambda function' }
  | { readonly value: DynamoDBResourceType; readonly label: 'DynamoDB table' }
  | { readonly value: AuroraResourceType; readonly label: 'Amazon Aurora database' }
  | { readonly value: RdsPostgreSQLResourceType; readonly label: 'Amazon RDS for PostgreSQL' };

export const RESOURCE_TYPE_DEFINITIONS = [
  { value: ResourceTypes.S3, label: 'S3 bucket' },
  { value: ResourceTypes.Lambda, label: 'Lambda function' },
  { value: ResourceTypes.DynamoDB, label: 'DynamoDB table' },
  { value: ResourceTypes.Aurora, label: 'Amazon Aurora database' },
  { value: ResourceTypes.RdsPostgreSQL, label: 'Amazon RDS for PostgreSQL' },
] as const satisfies readonly ResourceTypeDefinition[];

export const RESOURCE_TYPES = RESOURCE_TYPE_DEFINITIONS.map(({ value }) => value) as [
  ResourceType,
  ...ResourceType[],
];

export function resourceTypeLabel(value: ResourceType): string {
  return RESOURCE_TYPE_DEFINITIONS.find((definition) => definition.value === value)?.label ?? value;
}

export function isResourceType(value: string): value is ResourceType {
  return RESOURCE_TYPES.some((resourceType) => resourceType === value);
}

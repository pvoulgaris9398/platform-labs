import type { ResourceRequest, ResourceType } from './types';

export interface ResourceLink {
  readonly href: string;
  readonly label: string;
}

type ProvisionedService = ResourceType;

function serviceFromArn(arn: string): ProvisionedService | null {
  if (arn.startsWith('arn:aws:s3:::')) return 's3';
  if (arn.startsWith('arn:aws:lambda:')) return 'lambda';
  if (arn.startsWith('arn:aws:dynamodb:')) return 'dynamodb';
  if (arn.startsWith('arn:aws:rds:') && arn.includes(':cluster:')) return 'aurora';
  if (arn.startsWith('arn:aws:rds:') && arn.includes(':db:')) return 'rds_postgresql';
  return null;
}

function provisionedService(request: ResourceRequest): ProvisionedService {
  return serviceFromArn(request.provisioned_arn ?? '') ?? request.resource_type;
}

export function buildResourceLink(
  request: ResourceRequest,
  ministackEndpoint: string,
): ResourceLink | null {
  if (request.status !== 'provisioned') return null;

  const endpoint = ministackEndpoint.replace(/\/$/, '');
  const service = provisionedService(request);

  switch (service) {
    case 's3':
      return {
        href: `${endpoint}/${request.resource_name}`,
        label: `https://${request.resource_name}.s3.${request.region}.amazonaws.com`,
      };
    case 'lambda':
      return {
        href: `${endpoint}/2015-03-31/functions/${request.resource_name}`,
        label: `https://${request.region}.console.aws.amazon.com/lambda/home?region=${request.region}#/functions/${request.resource_name}`,
      };
    case 'dynamodb':
      return {
        href: `${endpoint}/`,
        label: `https://${request.region}.console.aws.amazon.com/dynamodbv2/home?region=${request.region}#table?name=${request.resource_name}`,
      };
    case 'aurora':
      return {
        href: `${endpoint}/`,
        label: `https://${request.region}.console.aws.amazon.com/rds/home?region=${request.region}#database:id=${request.resource_name};is-cluster=true`,
      };
    case 'rds_postgresql':
      return {
        href: `${endpoint}/`,
        label: `https://${request.region}.console.aws.amazon.com/rds/home?region=${request.region}#database:id=${request.resource_name};is-cluster=false`,
      };
  }
}

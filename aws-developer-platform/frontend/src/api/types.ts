export type ResourceType = 's3' | 'lambda' | 'dynamodb';

export interface Identity {
  readonly principal_arn: string;
  readonly display_name: string;
  readonly email: string;
  readonly team: string;
  readonly role: 'Developer' | 'Team_Lead' | 'Platform_Admin';
}

export interface Project {
  readonly id: string;
  readonly name: string;
  readonly application_name: string;
  readonly team_name: string;
  readonly allowed_environments: readonly string[];
}

export interface ResourceRequest {
  readonly id: string;
  readonly project_id: string;
  readonly resource_type: ResourceType;
  readonly resource_name: string;
  readonly region: string;
  readonly environment: string;
  readonly status: string;
  readonly estimated_monthly_cost_usd: string | null;
  readonly guardrail_warnings: readonly GuardrailWarning[];
  readonly expiry_date: string;
}

export interface GuardrailWarning {
  readonly rule_id: string;
  readonly rule_name: string;
  readonly message: string;
  readonly remediation: string;
}

export interface Envelope<T> {
  readonly data: T | null;
  readonly error: { readonly code: string; readonly message: string } | null;
}

output "audit_bucket_arn" { value = module.audit.bucket_arn }
output "database_endpoint" {
  value     = module.database.endpoint
  sensitive = true
}
output "service_name" { value = module.service.service_name }

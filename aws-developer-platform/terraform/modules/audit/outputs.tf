output "bucket_arn" { value = aws_s3_bucket.audit.arn }
output "log_group_arn" { value = aws_cloudwatch_log_group.audit.arn }

resource "aws_cloudwatch_log_group" "audit" {
  name              = "/platform/${var.name}/audit"
  retention_in_days = 90
  tags              = var.tags
}

resource "aws_s3_bucket" "audit" {
  bucket              = var.name
  object_lock_enabled = true
  tags                = var.tags
  lifecycle { prevent_destroy = true }
}

resource "aws_s3_bucket_versioning" "audit" {
  bucket = aws_s3_bucket.audit.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_public_access_block" "audit" {
  bucket                  = aws_s3_bucket.audit.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "audit" {
  bucket = aws_s3_bucket.audit.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

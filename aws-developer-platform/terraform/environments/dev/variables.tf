variable "aws_region" {
  type    = string
  default = "us-east-1"
}
variable "account_id" { type = string }
variable "image_digest" {
  type = string
  validation {
    condition     = can(regex("@sha256:[0-9a-f]{64}$", var.image_digest))
    error_message = "Use an immutable container digest."
  }
}
variable "tags" {
  type = map(string)
  validation {
    condition     = length(setsubtract(toset(["cost_center", "environment", "team", "owner", "project", "application_name", "expiry_date", "created_by"]), toset(keys(var.tags)))) == 0
    error_message = "All standard platform tags are required."
  }
}

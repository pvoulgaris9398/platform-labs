terraform {
  required_version = ">= 1.6.0, < 2.0.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.10.0"
    }
  }
  backend "s3" {
    key          = "aws-developer-platform/dev/terraform.tfstate"
    encrypt      = true
    use_lockfile = true
  }
}
provider "aws" {
  region = var.aws_region
  default_tags {
    tags = var.tags
  }
}

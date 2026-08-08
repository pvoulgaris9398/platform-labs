resource "aws_db_subnet_group" "this" {
  name       = var.name
  subnet_ids = var.subnet_ids
  tags       = var.tags
}

resource "aws_rds_cluster" "this" {
  cluster_identifier              = var.name
  engine                          = "aurora-postgresql"
  engine_mode                     = "provisioned"
  database_name                   = "platform"
  master_username                 = "platform_admin"
  manage_master_user_password     = true
  backup_retention_period         = 7
  storage_encrypted               = true
  db_subnet_group_name            = aws_db_subnet_group.this.name
  vpc_security_group_ids          = var.security_group_ids
  deletion_protection             = true
  enabled_cloudwatch_logs_exports = ["postgresql"]
  tags                            = var.tags
  lifecycle { prevent_destroy = true }
}

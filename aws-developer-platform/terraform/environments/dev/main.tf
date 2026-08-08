module "network" {
  source             = "../../modules/network"
  name               = "platform-dev"
  vpc_cidr           = "10.40.0.0/16"
  availability_zones = ["${var.aws_region}a", "${var.aws_region}b"]
  tags               = var.tags
}

module "audit" {
  source = "../../modules/audit"
  name   = "platform-audit-${var.account_id}"
  tags   = var.tags
}

module "database" {
  source             = "../../modules/database"
  name               = "platform-dev"
  subnet_ids         = module.network.private_subnet_ids
  security_group_ids = [module.network.database_security_group_id]
  tags               = var.tags
}

resource "aws_ecs_cluster" "this" {
  name = "platform-dev"
  tags = var.tags
}

data "aws_iam_policy_document" "ecs_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "execution" {
  name               = "platform-dev-execution"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
  tags               = var.tags
}

resource "aws_iam_role" "task" {
  name               = "platform-dev-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
  tags               = var.tags
}

module "service" {
  source              = "../../modules/service"
  name                = "platform-dev"
  cluster_arn         = aws_ecs_cluster.this.arn
  subnet_ids          = module.network.private_subnet_ids
  security_group_ids  = [module.network.api_security_group_id]
  image_digest        = var.image_digest
  execution_role_arn  = aws_iam_role.execution.arn
  task_role_arn       = aws_iam_role.task.arn
  database_secret_arn = module.database.secret_arn
  tags                = var.tags
}

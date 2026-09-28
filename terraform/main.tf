locals {
  build_dir = "${path.root}/../build"
}

module "network" {
  source = "./modules/network"

  name = var.project
}

module "database" {
  source = "./modules/database"

  name              = "${var.project}-db"
  subnet_ids        = module.network.subnet_ids
  security_group_id = module.network.security_group_id
}

module "storage" {
  source = "./modules/storage"

  name = "${var.project}-artifacts"
}

module "messaging" {
  source = "./modules/messaging"

  name                       = "${var.project}-transactions"
  visibility_timeout_seconds = var.visibility_timeout_seconds
  max_receive_count          = var.max_receive_count
}

module "processor" {
  source = "./modules/lambda_function"

  name       = "${var.project}-processor"
  source_dir = "${local.build_dir}/lambda/processor"
  build_dir  = local.build_dir
  handler    = "payments.processor.handler.handler"

  # The function has to give up before SQS shows the message to anyone else.
  timeout = var.visibility_timeout_seconds - 5

  environment = {
    DB_SECRET_ARN           = module.database.secret_arn
    MAX_AMOUNT              = var.max_amount
    BLOCKED_COUNTRIES       = join(",", var.blocked_countries)
    VELOCITY_LIMIT          = var.velocity_limit
    VELOCITY_WINDOW_MINUTES = var.velocity_window_minutes
  }

  policy_statements = [
    {
      sid       = "ConsumeTransactions"
      actions   = ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"]
      resources = [module.messaging.queue_arn]
    },
    {
      sid       = "ReadDatabaseCredentials"
      actions   = ["secretsmanager:GetSecretValue"]
      resources = [module.database.secret_arn]
    },
  ]
}

resource "aws_lambda_event_source_mapping" "transactions" {
  event_source_arn = module.messaging.queue_arn
  function_name    = module.processor.arn

  batch_size                         = 10
  maximum_batching_window_in_seconds = 1

  # Otherwise one bad message fails the whole batch and its healthy neighbours are
  # delivered again.
  function_response_types = ["ReportBatchItemFailures"]
}

module "api" {
  source = "./modules/ecs_api"

  name      = "${var.project}-api"
  region    = var.region
  image_tag = var.api_image_tag

  vpc_id            = module.network.vpc_id
  subnet_ids        = module.network.subnet_ids
  security_group_id = module.network.security_group_id

  environment = {
    DB_SECRET_ARN = module.database.secret_arn
    QUEUE_URL     = module.messaging.queue_url
  }

  policy_statements = [
    {
      sid       = "SubmitTransactions"
      actions   = ["sqs:SendMessage"]
      resources = [module.messaging.queue_arn]
    },
    {
      sid       = "ReadDatabaseCredentials"
      actions   = ["secretsmanager:GetSecretValue"]
      resources = [module.database.secret_arn]
    },
  ]
}

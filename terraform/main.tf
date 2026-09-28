locals {
  build_dir = "${path.root}/../build"
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
    DECISIONS_BUCKET        = module.storage.bucket
    DECISIONS_PREFIX        = "decisions"
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
      sid       = "WriteDecisions"
      actions   = ["s3:PutObject"]
      resources = ["${module.storage.arn}/decisions/*"]
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

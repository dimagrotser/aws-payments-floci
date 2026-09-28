variables {
  project = "tftest"
}

run "the_function_gives_up_before_sqs_redelivers" {
  command = plan

  assert {
    condition     = module.processor.timeout < var.visibility_timeout_seconds
    error_message = "the function must finish before SQS shows the message to anyone else"
  }
}

run "the_dead_letter_queue_is_named_after_its_source" {
  command = plan

  assert {
    condition     = module.messaging.dlq_name == "${module.messaging.queue_name}-dlq"
    error_message = "the dead letter queue should be obvious from the name of its source queue"
  }
}

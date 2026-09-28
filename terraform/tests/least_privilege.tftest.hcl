# Actions are known before anything is applied, so a stray wildcard is caught here, for
# free, without a running emulator. The resources those actions apply to are only known
# after apply, and tests/integration/test_least_privilege.py checks those against the
# deployed role using the same evaluator Floci uses at request time.

variables {
  project = "tftest"
}

run "nothing_is_granted_with_a_wildcard" {
  command = plan

  assert {
    condition     = !contains(module.processor.granted_actions, "*")
    error_message = "no function may be granted every action"
  }

  assert {
    condition = length([
      for action in module.processor.granted_actions : action if endswith(action, ":*")
    ]) == 0
    error_message = "no function may be granted every action of a service"
  }
}

run "the_processor_only_writes_to_s3" {
  command = plan

  assert {
    condition = [
      for action in module.processor.granted_actions : action if startswith(action, "s3:")
    ] == ["s3:PutObject"]
    error_message = "the processor should write decisions and nothing more"
  }
}

run "the_processor_does_not_produce_transactions" {
  command = plan

  assert {
    condition     = !contains(module.processor.granted_actions, "sqs:SendMessage")
    error_message = "submitting transactions is the API's job, not the processor's"
  }
}

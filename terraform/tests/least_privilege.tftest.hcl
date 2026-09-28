# Actions are known before apply; the resources they apply to are not, so those are
# checked against the deployed role in tests/integration/test_least_privilege.py.

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

run "the_processor_touches_no_storage_of_its_own" {
  command = plan

  assert {
    condition = length([
      for action in module.processor.granted_actions : action if startswith(action, "s3:")
    ]) == 0
    error_message = "the processor writes to the database, not to the bucket"
  }
}

run "the_processor_only_reads_the_secret" {
  command = plan

  assert {
    condition = [
      for action in module.processor.granted_actions :
      action if startswith(action, "secretsmanager:")
    ] == ["secretsmanager:GetSecretValue"]
    error_message = "reading the credentials is all the processor needs"
  }
}

run "the_processor_does_not_produce_transactions" {
  command = plan

  assert {
    condition     = !contains(module.processor.granted_actions, "sqs:SendMessage")
    error_message = "submitting transactions is the API's job, not the processor's"
  }
}

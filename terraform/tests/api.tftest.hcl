variables {
  project = "tftest"
}

run "the_application_and_the_agent_have_separate_roles" {
  command = plan

  assert {
    condition = length(setintersection(
      toset(module.api.granted_actions),
      toset(module.api.execution_granted_actions)
    )) == 0
    error_message = "pulling the image and running the application should share no permissions"
  }
}

run "the_application_only_produces_transactions" {
  command = plan

  assert {
    condition = [
      for action in module.api.granted_actions : action if startswith(action, "sqs:")
    ] == ["sqs:SendMessage"]
    error_message = "consuming the queue is the processor's job, not the API's"
  }
}

run "the_application_only_reads_the_secret" {
  command = plan

  assert {
    condition = [
      for action in module.api.granted_actions :
      action if startswith(action, "secretsmanager:")
    ] == ["secretsmanager:GetSecretValue"]
    error_message = "reading the credentials is all the API needs"
  }
}

run "the_agent_cannot_reach_the_application_data" {
  command = plan

  assert {
    condition = length([
      for action in module.api.execution_granted_actions :
      action if startswith(action, "sqs:") || startswith(action, "secretsmanager:")
    ]) == 0
    error_message = "the execution role pulls images and writes logs, nothing else"
  }
}

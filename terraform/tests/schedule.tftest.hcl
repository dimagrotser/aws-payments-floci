variables {
  project = "tftest"
}

run "the_report_runs_on_a_cron_not_a_rate" {
  command = plan

  assert {
    condition     = startswith(module.daily_report.schedule_expression, "cron(")
    error_message = "a daily report belongs at a fixed hour, not every N hours after deploy"
  }
}

run "the_reporter_writes_only_its_own_prefix" {
  command = plan

  assert {
    condition = [
      for action in module.reporter.granted_actions : action if startswith(action, "s3:")
    ] == ["s3:PutObject"]
    error_message = "the reporter writes the report and reads nothing back"
  }
}

run "the_reporter_is_not_on_the_queue" {
  command = plan

  assert {
    condition = length([
      for action in module.reporter.granted_actions : action if startswith(action, "sqs:")
    ]) == 0
    error_message = "the reporter has no business on the transaction queue"
  }
}

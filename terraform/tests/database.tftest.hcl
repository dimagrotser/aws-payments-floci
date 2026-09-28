variables {
  project = "tftest"
}

run "the_master_password_stays_out_of_the_state_file" {
  command = plan

  assert {
    condition     = module.database.password_in_state == false
    error_message = "the password must be passed through write-only arguments only"
  }
}

run "the_database_is_not_reachable_from_outside_the_vpc" {
  command = plan

  assert {
    condition     = module.database.publicly_accessible == false
    error_message = "a database on a public address is a finding, not a feature"
  }
}

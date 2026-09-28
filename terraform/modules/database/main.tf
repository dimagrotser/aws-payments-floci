# The master password is generated as an ephemeral value and handed over through
# write-only arguments, so it never reaches the state file. Both consumers are written
# on the same apply, which is what keeps the instance and the secret in agreement.
ephemeral "random_password" "master" {
  length           = 32
  override_special = "!#$%*()-_=+[]{}:?"
}

resource "aws_db_subnet_group" "this" {
  name       = var.name
  subnet_ids = var.subnet_ids
}

resource "aws_db_instance" "this" {
  identifier = var.name

  engine            = "postgres"
  engine_version    = var.engine_version
  instance_class    = var.instance_class
  allocated_storage = var.allocated_storage
  storage_encrypted = true

  db_name  = var.database_name
  username = var.master_username

  password_wo         = ephemeral.random_password.master.result
  password_wo_version = var.password_version

  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [var.security_group_id]
  publicly_accessible    = false

  skip_final_snapshot = true
  apply_immediately   = true
}

resource "aws_secretsmanager_secret" "this" {
  name                    = "${var.name}/master"
  description             = "Master credentials for ${var.name}"
  recovery_window_in_days = 0
}

# The shape AWS itself uses for RDS secrets, so the consumers need no custom parsing.
resource "aws_secretsmanager_secret_version" "this" {
  secret_id = aws_secretsmanager_secret.this.id

  secret_string_wo = jsonencode({
    engine   = "postgres"
    host     = aws_db_instance.this.address
    port     = aws_db_instance.this.port
    dbname   = aws_db_instance.this.db_name
    username = var.master_username
    password = ephemeral.random_password.master.result
  })
  secret_string_wo_version = var.password_version
}

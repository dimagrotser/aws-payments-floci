# Terraform runs inside the compose network (see scripts/tf.sh), so Floci is reachable
# under the name it advertises to Lambda and ECS containers too. One endpoint, no
# host-versus-container branching anywhere in this directory.
locals {
  floci_endpoint = "http://floci:4566"
}

provider "aws" {
  region = var.region

  # Floci accepts any credentials. They come from the environment (scripts/tf.sh) so
  # that not even a dummy key pair is written down in the repository.
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true
  s3_use_path_style           = true

  # The endpoint has to be listed per service; there is no global override.
  endpoints {
    iam    = local.floci_endpoint
    lambda = local.floci_endpoint
    logs   = local.floci_endpoint
    s3     = local.floci_endpoint
    sqs    = local.floci_endpoint
    sts    = local.floci_endpoint
  }

  default_tags {
    tags = {
      Project   = var.project
      ManagedBy = "terraform"
    }
  }
}
